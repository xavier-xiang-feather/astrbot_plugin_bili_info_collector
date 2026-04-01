from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api import logger
from astrbot.core.knowledge_base.kb_mgr import KnowledgeBaseManager
from astrbot.core.knowledge_base.kb_helper import KBHelper

from bilibili_api import dynamic, user, video
from .config import PluginConfig
import datetime


class KnowledgeBaseHelper:
    def __init__(self, context):
        self.context = context
        self.kb_manager = None
        self.kb_helper = None
        self.video_kb_helper = None
        self.dynamics_kb_helper = None

    async def initialize(self):
        
        
        provider = self.context.provider_manager
        self.kb_manager = KnowledgeBaseManager(provider)
        await self.kb_manager.initialize()
    
        #name of the knowledge base for testing: kb_test
        self.kb_helper = await self.kb_manager.get_kb_by_name("kb_test")
        self.video_kb_helper = await self.kb_manager.get_kb_by_name("yousa_videos")
        self.dynamics_kb_helper = await self.kb_manager.get_kb_by_name("yousa_dynamics")

    async def add_text(self, input_str: str, category: str, name = "new_doc" ) -> None:
        '''
        input_str: 添加到知识库的内容
        category: 内容的分类 "video"或"dynamic"
        name: 上传知识库时使用的文件名,默认是new_doc

        input_str: content to add to the knowledge base
        category: category of the content: "video" or "dynamic"
        name: name of the file when uploading to knowledge base, default: new_doc
        '''
        if self.video_kb_helper is None:
            raise Exception("视频知识库未初始化")
        if self.dynamics_kb_helper is None:
            raise Exception("动态知识库未初始化")
        

        if category == "video":
            await self.video_kb_helper.upload_document(
                file_name = name,
                file_content = None,
                file_type = "txt",
                pre_chunked_text = [input_str]
            )
        elif category == "dynamic":
            await self.dynamics_kb_helper.upload_document(
                file_name = name, 
                file_content = None,
                file_type = "txt",
                pre_chunked_text = [input_str]
            )
        else:
            raise ValueError("无效的分类，请选择'video'或'dynamic'")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        pass

class ScrapeHelper:
    def __init__(self, cred):
        self.cred = cred

    async def initialize(self):
        pass
    async def get_video(self, bvid: str) -> dict:
        '''
        input: 视频的bv号
        output: bilibili_api获取的视频信息字典

        input: bvid of the video
        output: video information dictionary got from bilibili_api
        '''
        v = video.Video(bvid=bvid, credential=self.cred)
        info = await v.get_info()
        return info
    
    async def get_dy(self, dynamic_id: int) -> dict:
        '''
        input: 动态id
        output: bilibili_api获取的动态信息字典

        input: dynamic id
        output: dynamic information dictionary got from bilibili_api
        '''
        dy = dynamic.Dynamic(dynamic_id, credential=self.cred)
        info = await dy.get_info()
        return info
    
#提取关键信息(单个投稿)，存进dict
    def extract_video(self, info: dict) -> dict:
        '''
        input: bilibili api获取的视频信息字典
        output: 提取关键信息后的字典

        input: video information dictionary got from bilibili_api
        output: dictionary after extracting key information
        '''
        output = {}
        output['标题'] = info.get('title','')
        output['作者'] = info['owner']['name']
        staff_list = info.get('staff', [])
        if staff_list:
            members = []
            for member in staff_list:
                name = member.get('name','')
                role = member.get('title','') if member.get('title') else ''
                members.append(f'{name}({role})')
            output['联合投稿人'] = ','.join(members)
        #如果没有联合投稿人，不加
        output['av号'] = info['aid']
        output['BV号'] = info['bvid']
        output['发布日期'] =(
            datetime.datetime.fromtimestamp(info['pubdate']).strftime('%Y年%m月%d日'))
        intro_sentence = info['desc']
        output['视频简介'] = intro_sentence.replace('\n', '; ')
        stats = info['stat']
        output['播放量'] = stats['view']
        output['点赞量'] = stats['like']
        output['投币数'] = stats['coin']
        output['收藏量'] = stats['favorite']
        output['转发量'] = stats['share']
        output['信息获取时间'] = datetime.datetime.now().strftime('%Y年%m月%d日')
        vid_duration = info['pages'][0]['duration'] if info['pages'] else 0
        vid_min = vid_duration // 60
        vid_sec = vid_duration % 60
        output['视频时长'] = f"{vid_min}分{vid_sec:02d}秒"
        return output


    def extract_dynamic(self, info: dict) -> dict:
        '''
        input: bilibili_api获取的动态信息字典。注:该字典由get_dynamic_new获取
        output: 提取关键信息后的字典

        input: dynamic information dictionary got from bilibili_api. Note: this dictionary is obtained from get_dynamic_new()
        output: dictionary after extracting key information
        '''
        try: 
            output = {}
            module_author = info['item']['modules']['module_author']
            module_dynamic = info['item']['modules']['module_dynamic']
            output['作者'] = module_author['name']
            did = info['item'].get('id_str', '未知动态id')
            output['动态ID'] = did
            output['发布时间'] = module_author['pub_time']
            #动态
            if (module_author.get('pub_action') == ''):
                #有major说明没有转发其它内容
                if (module_dynamic.get('major')):
                    content = module_dynamic.get('major',{}).get('opus',{}).get('summary',{}).get('text','无内容')
                    output['动态内容'] = content 

                #major是null说明是转发了其它内容    
                else:
                    content = module_dynamic.get('desc',{}).get('text','无内容')
                    output['动态内容'] = content
                    #转发了视频
                    video_pub_action = info['item']['orig']['modules']['module_author']['pub_action']
                    if (video_pub_action == '投稿了视频' or video_pub_action == '与他人联合创作'):
                        video = info['item']['orig']['modules']['module_dynamic']['major']['archive']
                        output['转发的视频标题'] = video.get('title','')
                        output['转发的视频BV号'] = video.get('bvid','')
                        output['转发的视频简介'] = video.get('desc','')

                    #转发了动态
                    elif (info['item']['orig']['modules']['module_author']['pub_action'] == ''): 
                        other_dy = info['item']['orig']['modules']
                        output['转发的动态作者'] = other_dy['module_author'].get('name','')
                        
                        #保险起见，如果转发的动态转发了另一个动态
                        if other_dy['module_dynamic'].get('major'):
                            output['转发的动态内容'] = other_dy['module_dynamic'].get('major',{}).get('opus',{}).get('summary',{}).get('text','')
                        else:
                            output['转发的动态内容'] = '未知转发动态内容'

                        output['转发的动态主题'] = (other_dy['module_dynamic'].get('topic') or {}).get('name','无主题')

            
            elif module_author.get('pub_action') == '发布了动态视频':
                #有动态视频 
                major = module_dynamic.get('major') or {}
                output['动态视频标题'] = major.get('archive',{}).get('title','未知动态标题')
                output['动态视频BV号'] = major.get('archive',{}).get('bvid','未知动态bv号')
                output['动态视频简介'] = major.get('archive',{}).get('desc','')
            else:
                output['动态内容'] = '未知动态内容，需要检查'

            return output
        
        except Exception as e:
            did = info.get('id_str', '未知动态id')
            logger.error(f"错误类型:", e)
            logger.info(f"解析动态出错!动态ID:{did}")


    def format_info(self, info: dict) -> str:
        '''
        input: extract后的output字典
        output: 格式化成str写入知识库

        input: output dictionary after extract
        output: formatted into str for writing into knowledge base
        '''
        if info is None:
            logger.info("info为空")
            return 
        body = "\n".join(f"{key}:{value}" for key, value in info.items())
        return "{\n" + body + "\n}\n\n"
        
class MonitorHelper:
    def __init__(self, cred):
        self.cred = cred

    async def initialize(self):
        pass

    async def get_latest_dynamics(self, u: user.User) -> dict:
        try:
            latest_dynamics = await u.get_dynamics_new(offset='')

            items = latest_dynamics.get('items', [])
            if items:
                first_dynamic = latest_dynamics.get('items',[])[0]

                #删除置顶动态
                if first_dynamic and first_dynamic.get('modules',{}).get('module_tag') is not None:
                    del latest_dynamics['items'][0]
                return latest_dynamics
            else:
                return {"items": []}

        except Exception as e:
            logger.info(f"动态获取失败\n {e}")
            return {"items": []}
        
    async def get_user(self, uid: int) -> user.User:
        return user.User(uid=uid, credential=self.cred)