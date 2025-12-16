import sys
import os
import datetime
import autogen
import re
from config import config_tongyi  # 只导入通义配置
from game_prompts import (
    MODERATOR_PROMPT, 
    WEREWOLF_PROMPT, 
    VILLAGER_PROMPT, 
    SEER_PROMPT,
    WITCH_PROMPT,
    HUNTER_PROMPT
)

# --- 日志记录类 ---
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush() # 确保实时写入

    def flush(self):
        self.terminal.flush()
        self.log.flush()

class PrivateThoughtGroupChat(autogen.GroupChat):
    """
    自定义的群聊类。
    功能：在将消息存入群聊历史（Memory）之前，剔除 (INNER_THOUGHT: ...) 的内容。
    这样其他 Agent 就看不到内心独白，但屏幕和日志依然会显示（因为日志打印发生在 append 之前）。
    """
    def append(self, message, speaker):
        # 1. 获取原始内容
        original_content = message["content"]
        
        # 2. 如果内容不为空，进行清洗
        if original_content:
            # 正则解释：匹配 (INNER_THOUGHT: 开始，直到 ) 结束的所有内容
            # flags=re.DOTALL 让 . 能够匹配换行符
            cleaned_content = re.sub(
                r'\(INNER_THOUGHT:.*?\)', 
                '', 
                original_content, 
                flags=re.DOTALL
            ).strip()
            
            # 如果清洗后只剩下 "PUBLIC_SPEECH:" 这种空头衔，也顺手清理一下（可选）
            cleaned_content = cleaned_content.replace("PUBLIC_SPEECH:", "").strip()
            
            # 3. 创建一个新的消息对象，以免修改原始引用导致日志也变了
            # 注意：我们只修改存入历史的消息，不修改 agent 返回的原始消息
            message = message.copy()
            message["content"] = cleaned_content

        # 4. 调用父类的 append 方法将清洗后的消息存入历史
        super().append(message, speaker)

def main():
    # 1. 设置日志文件名 (格式: 2023-10-27_10-30-00.log)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"{timestamp}.log"
    
    # 2. 重定向输出
    sys.stdout = Logger(log_filename)
    print(f"=== 游戏日志已开始记录: {log_filename} ===")
    print("=== 配置: 9人标准局 (3狼/3民/1预/1女/1猎) | 全员通义千问 ===")

    # 3. 创建法官
    moderator = autogen.AssistantAgent(
        name="法官",
        system_message=MODERATOR_PROMPT,
        llm_config=config_tongyi,
    )

    # 4. 创建玩家列表
    agents = []

    # --- 狼人阵营 (3人) ---
    for i in range(1, 4):
        wolf = autogen.AssistantAgent(
            name=f"狼人_{i}号",
            system_message=WEREWOLF_PROMPT,
            llm_config=config_tongyi,
            description=f"玩家，身份是狼人，编号{i}。"
        )
        agents.append(wolf)

    # --- 神职阵营 (3人) ---
    seer = autogen.AssistantAgent(
        name="预言家_4号",
        system_message=SEER_PROMPT,
        llm_config=config_tongyi,
        description="玩家，身份是预言家，编号4。"
    )
    agents.append(seer)

    witch = autogen.AssistantAgent(
        name="女巫_5号",
        system_message=WITCH_PROMPT,
        llm_config=config_tongyi,
        description="玩家，身份是女巫，编号5。"
    )
    agents.append(witch)

    hunter = autogen.AssistantAgent(
        name="猎人_6号",
        system_message=HUNTER_PROMPT,
        llm_config=config_tongyi,
        description="玩家，身份是猎人，编号6。"
    )
    agents.append(hunter)

    # --- 平民阵营 (3人) ---
    for i in range(7, 10):
        villager = autogen.AssistantAgent(
            name=f"平民_{i}号",
            system_message=VILLAGER_PROMPT,
            llm_config=config_tongyi,
            description=f"玩家，身份是平民，编号{i}。"
        )
        agents.append(villager)

    # 5. 创建用户代理 (用于触发游戏)
    user_proxy = autogen.UserProxyAgent(
        name="User_Admin",
        system_message="我是游戏管理员。",
        code_execution_config=False,
        human_input_mode="NEVER",
        is_termination_msg=lambda x: "GAME_OVER" in x.get("content", "")
    )

    # 6. 将所有角色加入群聊列表 (包括法官和用户代理)
    all_participants = [user_proxy, moderator] + agents

    # 7. 创建群聊
    # groupchat = autogen.GroupChat(
    #     agents=all_participants,
    #     messages=[],
    #     max_round=20, # 9人局回合数可以设多一点
    #     speaker_selection_method="auto"
    # )
    
    groupchat = PrivateThoughtGroupChat(
        agents=all_participants,
        messages=[],
        max_round=20,
        speaker_selection_method="auto"
    )

    # 8. 创建管理器
    manager = autogen.GroupChatManager(
        groupchat=groupchat, 
        llm_config=config_tongyi
    )

    # 9. 构造初始场景 Prompt
    player_names = [agent.name for agent in agents]
    initial_scenario = f"""
    【游戏开始】
    这是一个9人标准局。
    玩家名单：{', '.join(player_names)}。
    
    现在是第一天白天。
    昨晚平安夜，没有人死亡（或者你可以随机生成一个昨晚的情况）。
    现在请【法官】主持游戏，安排大家开始竞选警长或轮流发言。
    """

    # 10. 开始游戏
    user_proxy.initiate_chat(
        manager,
        message=initial_scenario
    )

if __name__ == "__main__":
    main()