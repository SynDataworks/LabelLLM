import pandas as pd
import uuid
import json
import re

rules = """
请判断该搜索词是以下列表中哪种类型["游戏名搜索", "实体", "游戏综合型攻略", "游戏细节玩法搜索", "搜索某类游戏", "其他内容搜索"]。

# 游戏名搜索
- 搜索的目标是游戏名，例如“原神”、“崩坏3”等
- 想要寻找某个游戏，但是名称没有输入完整，或者没有记住游戏名，尝试用相近的名字去搜索
- 寻找具体的游戏区服，例如“官服”、“体验服”、“赛季服”、”测试服“等

# 实体
- 游戏中的角色、职业、道具、装备、技能、载具、宠物、货币等实体。例如“张飞”、“赵云”、“原神钟离”、“崩坏星穹铁道香菱”等
- 搜索按照“游戏名+实体”的形式，例如“原神钟离”、“崩坏星穹铁道香菱”等
- 动漫、影视、二次元等娱乐向内容中的实体，例如“路飞”、“柯南”等
- 游戏厂商、开发商等实体，例如“腾讯”、“网易”等

# 游戏综合型攻略
- 需要搜索完整、全面的攻略，例如“原神攻略”、“原神可莉攻略”、“心动小镇种地攻略”

# 游戏细节玩法搜索
- 搜索游戏中的某个具体玩法，相比于综合型攻略，会聚焦在具体某一类攻略上，例如“原神可莉配队攻略”、“赵云出装推荐”
- 搜索游戏中的福利，例如“绝区零 兑换码”
- 特殊的游戏版本，例如“98版”、“破解版”、“单机版”
- 想看玩家对某个内容的主观讨论，例如“王者荣耀新活动怎么样”
- 搜索某个任务、关卡、副本、活动、地图的攻略，例如“崩坏3第三章”、“”
- 和游戏相关的其他内容

# 搜索某类游戏
- 某类标签的游戏，例如“射击游戏”、“动作游戏”、“双人联机游戏”等
- 例如“类似原神的游戏”、“可以打造装备的游戏”
- 某个开发商的游戏，例如“腾讯游戏”、“网易游戏”

# 其他内容搜索
- 搜索不是游戏、动漫等娱乐向内容，更偏向生活日常类搜索，例如“如何提高英语口语”、“如何学习编程”等
- 无意义的内容或者无法判断的内容，例如随机数字、链接等
- 参考内容中缺乏足够的信息判断时，可以归类为此类别
- 无法被归为以上任何一类的搜索词

注意：参考内容和相关游戏名并非绝对准确，仅供参考。
"""

label_class = {
    'game_name': '游戏名搜索',
    'games': '某类游戏搜索',
    'game_details': "游戏细节玩法搜索",
    'game_strg': '游戏综合型攻略',
    'entity': '实体',
    'others': '其他内容搜索'
}

developers = ['腾讯', '网易', '叠纸', '雷火', '雷霆游戏', "mihoyo", "米游社",'游戏科学','游族',"三七",
              '紫龙','鹰角','祖龙','库洛','心动','易次元']
posfixs = ['体验服', '赛季服', '测试服', "先行服", "国际服", "先遣服"]

game_details_words = ['怎么样', '兑换码', '怎么', '配队', '组队', '搭配', '破解','单机版', '活动','联机',]
re_game_chapters = r"第\d{1,3}章|第\d{1,3}关|\d{1,3}-\d{1,3}|第[一二三四五六七八九十百千]{1,2}章|第[一二三四五六七八九十百千]{1,2}关"

game_details_pattern = "|".join(re.escape(sub) for sub in game_details_words)
preanotate_count = 0

def preanotate_query(query, related_game=None):
    query = query.lower()
    related_game = related_game.lower() if related_game else None
    r_game_pattern = rf"^{re.escape(related_game)}.{{4,}}"
    if query in related_game or any(pos in query for pos in posfixs):
        return 'game_name'
    elif '游戏' in query or any(dev in query for dev in developers):
        return 'games'
    elif re.search(game_details_pattern, query, re.IGNORECASE):
        return 'game_details'
    elif re.search(re_game_chapters, query, re.IGNORECASE):
        return 'game_details'
    elif '攻略' in query:
        return 'game_strg'
    # 匹配游戏名+多个字
    elif re.search(r_game_pattern, query):
        return 'game_details'
    else:
        return None
    


def trans_row2jsonl(row, namespace='游戏意图标注'):
    line_dict = {'prompt':'请判断该搜索词是以下列表中哪种类型：游戏名搜索, 实体, 游戏综合型攻略, 游戏细节玩法搜索, 搜索某类游戏, 其他内容搜索。'}
    query = row['query']
    relate_game = row['related_game']
    relate_game = str(relate_game) if relate_game else ""
    context = row['context']
    context = context.replace('#', ' ')
    # context = context.replace('---', '\---')
    context = context.replace('\n===\n', '\n\n\n')
    conversation = list()
    uuid4_str = str(uuid.uuid4())
    send_dict = {
            "message_id": uuid4_str,
            "content": query,
            "message_type": "send", # 消息类型，send类型会显示原始格式，不进行md渲染；receive类型会进行md渲染。
            "user_id": "1234",
            "parent_id": None
        }
    conversation.append(send_dict)
    recv_uuid4_str = str(uuid.uuid4())
    recv_dict1 = {
            "message_id": recv_uuid4_str,
            "content": '注意比对Tap游戏名:  '+ relate_game,
            "message_type": "receive",
            "user_id": "1234", # 指给回复的是哪个角色或用户
            "parent_id": uuid4_str, # 针对的是哪条send
        }
    conversation.append(recv_dict1)
    recv_uuid4_str2 = str(uuid.uuid4())
    recv_dict2 = {
            "message_id": recv_uuid4_str2,
            "content": context,
            "message_type": "receive",
            "user_id": "1234", #指给回复的是哪个角色或用户
            "parent_id": uuid4_str, #针对的是哪条send
        }
    conversation.append(recv_dict2)
    class1 = preanotate_query(query=query, related_game=relate_game)
    if class1:
        global preanotate_count 
        preanotate_count += 1
        reference_evaluation = {"conversation_evaluation": {"query_intention": class1}}
    else:
        reference_evaluation = None
    custom = {'remark':"简单预标注"}
    line_dict['conversation'] = conversation
    if reference_evaluation:
        line_dict['reference_evaluation'] = reference_evaluation
    line_dict['custom'] = custom
    
    return line_dict

def preprocess_excel(df, outpath):
    llist = df.apply(lambda row: json.dumps(trans_row2jsonl(row), ensure_ascii=False), axis=1)
    print(f'预标注数量一共{preanotate_count}条')
    jsonl_output = "\n".join(llist)
    with open(outpath, "w", encoding="utf-8") as file:
        file.write(jsonl_output)

if __name__ == '__main__':
    df = pd.read_excel('data/intention_data.xlsx',nrows=500, skiprows=lambda x: x in range(1, 6500))
    preprocess_excel(df, 'data/intention_data_test500.jsonl')