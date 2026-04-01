from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.core import AstrBotConfig
from astrbot.api import logger


from .utils import KnowledgeBaseHelper, ScrapeHelper, MonitorHelper
from .config import PluginConfig
from bilibili_api import Credential, user
import json
import os
import asyncio
import random


@register("yousaChannelHelper", "YourName", "yousa的视频/动态收集助手", "1.0.0")
class yousaChannelHelperPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.cfg = PluginConfig(config, context)
        self.kb_helper = KnowledgeBaseHelper(context)
        
        self.cred = Credential(
            sessdata=self.cfg.sessdata,
            bili_jct=self.cfg.bili_jct,
            buvid3=self.cfg.buvid3,
            buvid4=self.cfg.buvid4,
            dedeuserid=self.cfg.dedeuserid
        )
        self.scrape_helper = ScrapeHelper(self.cred)
        self.monitor_helper = MonitorHelper(self.cred)
        self.auto_update = True
        self.dir_path = self.cfg.dir_path


    async def initialize(self):
        await self.kb_helper.initialize()
        pass

    def _is_authorized(self, event: AstrMessageEvent) -> bool:
        if not self.cfg.whitelist:
            return False
        
        group_id = event.get_group_id()
        if group_id:
            return str(group_id) in [str(w) for w in self.cfg.whitelist]
        
        sender_id = event.get_sender_id()
        return str(sender_id) in [str(w) for w in self.cfg.whitelist]
    
    def _ensure_dir_exists(self) -> None:
        if not self.cfg.dir_path:
            logger.warning("未配置文件目录，无法储存动态记录")
            return
        os.makedirs(self.cfg.dir_path, exist_ok=True)
    def _get_file_path(self, uid:int) -> str:
        file_name = os.path.join(self.cfg.dir_path, f"latest_dynamic_{uid}.json")
        return file_name
    def _ensure_file_exists(self, path:str) -> None:
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({"dynamic": "12345"}, f)

    '''
    知识库更新----------------------------------------------------------------------------------
    update knowledge base
    '''
    @filter.command_group("kb")
    async def kb(self):
        pass

    @kb.command("add")
    async def add_kb(self, event:AstrMessageEvent):
        if not self._is_authorized(event):
            return
        
        try:
            content = event.message_str
            text = content.split(maxsplit=2)
            if len(text) < 3:
                yield event.plain_result("未输入要添加的内容")
                return
            input_str = text[2]
            await self.kb_helper.add_text(input_str)
            yield event.plain_result(f"你添加了:{input_str}")

        except Exception as e:
            yield event.plain_result("内容添加失败")
            logger.error(f"添加失败: {e}", exc_info=True)

    @kb.command("help")
    async def show_help(self, event: AstrMessageEvent):
        if not self._is_authorized(event):
            return
        help_text = """
        /kb add <内容> - 添加知识库内容
        """
        yield event.plain_result(help_text)
        event.stop_event()

    '''
    视频/动态爬虫----------------------------------------------------------------------------------
    video/dynamic collector
    '''
    @filter.command_group("scrape")
    async def scrape(self):
        pass

    @scrape.command("帮助")
    async def show_scrape_help(self, event: AstrMessageEvent):
        if not self._is_authorized(event):
            yield event.plain_result("无权限")
            return
        help_text = """
⚙️命令: /scrape 视频 <bv号>
📖说明: 根据bv号获取视频到知识库
💡例子: /scrape 视频 BV1TTAfzeEcX

⚙️命令: /scrape 动态 <动态ID>
📖说明: 根据动态ID获取动态到知识库
💡例子: /scrape 动态 1181705278093000710

⚙️命令: /自动更新 <UID>
📖说明: 根据UID自动监测动态并上传知识库
💡例子: /自动更新 282994

⚙️命令: /停止自动更新
📖说明: 将停止所有自动监测
💡例子: /停止自动更新
                    """
        yield event.plain_result(help_text)
        event.stop_event()
        

    @scrape.command("视频")
    async def scrape_video(self, event:AstrMessageEvent):
        if not self._is_authorized(event):
            return
        try:
            content = event.message_str
            text = content.split(maxsplit=2)
            if len(text) < 3:
                yield event.plain_result("未输入bv号")
                return
            bvid = text[2]
            info = await self.scrape_helper.get_video(bvid)
            logger.info("视频获取成功")

            info = self.scrape_helper.extract_video(info)
            file_name = info.get('标题', 'new_video')
            info = self.scrape_helper.format_info(info)

            await self.kb_helper.add_text(input_str=info, category="video", name=file_name)
            yield event.plain_result("视频添加至知识库成功")

        except Exception as e:
            yield event.plain_result("视频添加失败")
            logger.error(f"logger视频添加失败: {e}", exc_info=True)

    @scrape.command("动态")
    async def scrape_dynamic(self, event:AstrMessageEvent):
        if not self._is_authorized(event):
            return
        try:
            content = event.message_str
            text = content.split(maxsplit=2)
            if len(text) < 3:
                yield event.plain_result("未输入动态ID")
                return
            dy_id = int(text[2])
            info = await self.scrape_helper.get_dy(dy_id)
            logger.info("动态获取成功")

            info = self.scrape_helper.extract_dynamic(info)
            file_name = info.get('发布时间', 'new_dynamic')
            info = self.scrape_helper.format_info(info)
            await self.kb_helper.add_text(input_str=info, category="dynamic", name=file_name)
            yield event.plain_result("动态添加至知识库成功")

        except Exception as e:
            yield event.plain_result("动态添加失败")
            logger.error(f"logger动态添加失败: {e}", exc_info=True)

    '''
    自动监测----------------------------------------------------------------------------------
    auto monitor
    '''
    async def update_dynamics(self, u: user.User, path: str, event:AstrMessageEvent):
        
        latest_dynamics = await self.monitor_helper.get_latest_dynamics(u)
        has_new = False

        '''
        找到上一次储存的动态
        get last stored dynamic
        '''
        with open(path, 'r', encoding='utf-8') as f:
            stored_dynamics = json.load(f)

        last_dynamic = stored_dynamics.get('dynamic','')
        if not last_dynamic:
            last_dynamic = latest_dynamics.get('items',[])[0].get('id_str','')
            stored_dynamics['dynamic'] = last_dynamic
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(stored_dynamics, f, ensure_ascii=False, indent=2)
            return
            
        '''
        更新视频和动态
        update videos and dynamics
        '''
        for item in latest_dynamics.get('items',[]):
            if item.get('id_str') == last_dynamic:
                break
            has_new = True
            dy_type = item.get('type', '')
            if dy_type == "DYNAMIC_TYPE_AV":
                bvid = item.get('modules',{}).get('module_dynamic',{}).get('major',{}).get('archive',{}).get('bvid','')
                info = await self.scrape_helper.get_video(bvid)
                info = self.scrape_helper.extract_video(info)
                file_name = info.get('标题', 'new_video')
                info = self.scrape_helper.format_info(info)
                await self.kb_helper.add_text(input_str=info, category="video", name=file_name)
                yield event.plain_result(f"已上传视频:{file_name}")
            else:
                did = item.get('id_str','')
                info = await self.scrape_helper.get_dy(did)
                info = self.scrape_helper.extract_dynamic(info)
                file_name = info.get('发布时间', 'new_dynamic')
                info = self.scrape_helper.format_info(info)
                await self.kb_helper.add_text(input_str=info, category="dynamic", name=file_name)
                yield event.plain_result(f"已上传动态，发布时间:{file_name}")

        if has_new:
            latest_id = latest_dynamics.get('items',[])[0].get('id_str','')
            stored_dynamics['dynamic'] = latest_id
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(stored_dynamics, f, ensure_ascii=False, indent=2)

    @filter.command("自动更新")
    async def monitor_dynamics(self, event:AstrMessageEvent):
        if not self._is_authorized(event):
            return
        
        
        self.auto_update = True
        yield event.plain_result("自动更新已开启")
        try:
            content = event.message_str
            text = content.split(maxsplit=1)
            if len(text) < 2:
                yield event.plain_result("未输入UID")
                return
            uid = int(text[1])
        
            #检查文件
            self._ensure_dir_exists()
            file_path = self._get_file_path(uid)
            self._ensure_file_exists(file_path)

            u = user.User(uid=uid, credential=self.cred)
            while True:
                if self.auto_update is False:
                    yield event.plain_result("自动更新已停止")
                    break
                try:
                    async for msg in self.update_dynamics(u, file_path, event):
                        yield msg
                except Exception as e:
                    logger.error(f"获取/上传动态失败: {e}", exc_info=True)
                    yield event.plain_result("获取/上传动态失败")
                await asyncio.sleep(300)
                n = random.uniform(60,240)
                await asyncio.sleep(n)
        except Exception as e:
            yield event.plain_result("自动更新失败")
            logger.error(f"自动更新失败: {e}", exc_info=True)
    
    @filter.command("停止自动更新")
    async def stop_monitor(self, event:AstrMessageEvent):
        if not self._is_authorized(event):
            yield event.plain_result("无权限")
            return
        self.auto_update = False
        yield event.plain_result("停止自动更新已启用")
