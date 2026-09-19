# Bilibili Content Creator Monitor Plugin 

## Overview
This is a custom plugin designed for a knowledge-base chatbot system. It automatically monitors an influencer on Bilibili and updates the knowledge base with new content.

---

## Features

- Automatically monitors an influencer’s content using their UID  
- Detects new posts and videos  
- Extracts and structures content into a knowledge base  
- Supports both manual data ingestion and automated updates  

---

## Commands

- `/scrape 视频 <bvid>`  
  Manually fetch and upload video information to the knowledge base  

- `/scrape 动态 <did>`  
  Manually fetch and upload post (dynamic) information  

- `/自动更新 <UID>`  
  Start monitoring a specific influencer and automatically update new content  

- `/停止自动更新`  
  Stop all monitoring processes  

---

## Example
- `/自动更新 1234`  
  Starts automatically monitoring the influencer with UID `1234` and updates new content into the knowledge base.

## Tech Stack

- bilibili-api  

---
