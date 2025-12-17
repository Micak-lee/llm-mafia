import sys
import os
import re
import datetime
import random
import autogen
from collections import Counter
from config import config_tongyi 
from game_prompts import (
    WEREWOLF_PROMPT, 
    VILLAGER_PROMPT, 
    SEER_PROMPT, 
    WITCH_PROMPT,
    HUNTER_PROMPT
)

# ==============================================================================
# 1. 基础工具类
# ==============================================================================

class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()
    def flush(self):
        self.terminal.flush()
        self.log.flush()

class PrivateThoughtGroupChat(autogen.GroupChat):
    def append(self, message, speaker):
        original_content = message["content"]
        if original_content:
            cleaned = re.sub(r'\(INNER_THOUGHT:.*?\)', '', original_content, flags=re.DOTALL).strip()
            cleaned = cleaned.replace("PUBLIC_SPEECH:", "").strip()
            msg_copy = message.copy()
            msg_copy["content"] = cleaned
            super().append(msg_copy, speaker)
        else:
            super().append(message, speaker)

# ==============================================================================
# 2. 逻辑辅助函数
# ==============================================================================

def extract_target(content):
    if not content: return None
    match = re.search(r'(玩家_\d+号)', content)
    return match.group(1) if match else None

def extract_witch_decision(content):
    save = False
    poison_target = None
    if content:
        if "解药: 使用" in content or "救" in content:
            save = True
        if "毒药: 使用" in content:
            poison_target = extract_target(content)
    return save, poison_target

def check_victory(living_agents, identity_map):
    wolves = [a for a in living_agents if identity_map[a.name] == "狼人"]
    good = [a for a in living_agents if identity_map[a.name] != "狼人"]
    if len(wolves) == 0:
        return True, "好人胜利 (狼人全灭)"
    if len(wolves) >= len(good):
        return True, "狼人胜利 (屠城/绑票)"
    return False, None

# ==============================================================================
# 3. 游戏阶段逻辑 (Python 接管)
# ==============================================================================

from game_prompts import WOLF_NIGHT_INSTRUCTION, WEREWOLF_PROMPT # 确保导入

def run_night_logic(living_agents, identity_map, moderator, admin_proxy):
    print("\n" + "🌑 "*15 + "\n>>> 进入夜晚阶段\n" + "🌑 "*15)
    
    wolf_kill = None
    
    # ----------------- 1. 狼人行动 -----------------
    living_wolves = [a for a in living_agents if identity_map[a.name] == "狼人"]
    
    if living_wolves:
        print(f"🐺 狼人 ({len(living_wolves)}人) 正在商议...")
        
        # === 关键修改：切换为夜间 Prompt ===
        for wolf in living_wolves:
            # 临时覆盖 System Message
            # 我们把“狼人身份定义”和“夜间指令”拼起来
            night_sys_msg = f"你的身份是狼人。\n{WOLF_NIGHT_INSTRUCTION}"
            wolf.update_system_message(night_sys_msg)

        # 创建狼人聊天群
        wolf_group = autogen.GroupChat(
            agents=living_wolves, 
            messages=[], 
            max_round=5, 
            speaker_selection_method="auto"
        )
        wolf_manager = autogen.GroupChatManager(wolf_group, llm_config=config_tongyi)
        
        # 触发讨论
        admin_proxy.initiate_chat(
            wolf_manager,
            message="【系统】天黑了。狼人请睁眼。请商量击杀目标。",
            summary_method="last_msg"
        )
        
        # 解析结果 (保持不变)
        for msg in reversed(wolf_group.messages):
            if "决定击杀" in msg["content"]:
                wolf_kill = extract_target(msg["content"])
                if wolf_kill: break
        
        if not wolf_kill:
            # 随机刀逻辑... (保持不变)
            valid = [a.name for a in living_agents if identity_map[a.name] != "狼人"]
            if valid: 
                wolf_kill = random.choice(valid)
                print(f"⚠️ 狼人随机击杀: {wolf_kill}")
        else:
            print(f"🔴 狼人锁定: {wolf_kill}")

        # === 关键步骤：还原为白天 Prompt ===
        for wolf in living_wolves:
            wolf.update_system_message(WEREWOLF_PROMPT)

    # ... (后续预言家、女巫逻辑保持不变) ...
    
    return list(set(dead_list))

# --- 新增：警长竞选逻辑 ---
def run_sheriff_election(living_agents, admin_proxy):
    print("\n" + "👮 "*15 + "\n>>> 进入警长竞选环节\n" + "👮 "*15)
    
    # 1. 询问上警
    candidates = []
    print("系统询问：是否参与警长竞选？")
    for agent in living_agents:
        # 为了节省时间，我们只让前6号有机会上警，或者全员皆可
        # 这里简化：全员询问，max_turns=1
        admin_proxy.initiate_chat(
            agent,
            message="【系统】现在开始警长竞选。你想上警吗？\n如果要竞选，请回复：[我要竞选]。\n如果不竞选，请回复：[不竞选]。",
            max_turns=1
        )
        if "我要竞选" in agent.last_message()["content"]:
            candidates.append(agent)
            print(f"✋ {agent.name} 举手竞选！")
    
    if not candidates:
        print("⚠️ 无人竞选，本局无警长。")
        return None
        
    print(f"📋 警长候选人: {[c.name for c in candidates]}")
    
    # 2. 候选人发言 (简化版：每人一句话)
    # 实际应该有一个专门的 GroupChat
    print("🗣️ 候选人发表竞选演说...")
    for cand in candidates:
        admin_proxy.initiate_chat(
            cand,
            message=f"【系统】请发表竞选演说。说明你为什么要当警长。",
            max_turns=1
        )

    # 3. 投票 (非候选人投票)
    voters = [a for a in living_agents if a not in candidates]
    if not voters:
        print("⚠️ 所有人都上警了，无法投票，随机抽签。")
        return random.choice(candidates).name
        
    votes = []
    print("🗳️ 开始警长投票...")
    candidate_names = [c.name for c in candidates]
    
    for voter in voters:
        admin_proxy.initiate_chat(
            voter,
            message=f"【系统】请投票给警长候选人。可选：{', '.join(candidate_names)}。\n格式：[投票: 玩家_X号]。",
            max_turns=1
        )
        target = extract_target(voter.last_message()["content"])
        if target and target in candidate_names:
            print(f"👉 {voter.name} 投给了 {target}")
            votes.append(target)
        else:
            print(f"⚪ {voter.name} 弃票")
            
    # 统计
    if not votes:
        print("⚠️ 无人有效投票，本局无警长。")
        return None
        
    counts = Counter(votes)
    winner_name = counts.most_common(1)[0][0]
    print(f"🎉 恭喜 {winner_name} 当选警长！")
    return winner_name

def run_day_speech(living_agents, moderator, admin_proxy, death_announcement, sheriff_name=None):
    print("\n" + "☀️ "*15 + "\n>>> 进入白天发言阶段\n" + "☀️ "*15)
    
    # 构建发言列表
    # 如果有警长，通常警长最后发言或警长决定顺序。
    # 这里简化：如果有人当选警长，他在日志里会有个特殊标记，但顺序依然按座位（为了代码稳定性）
    
    speech_prefix = ""
    if sheriff_name:
        speech_prefix = f"【警长 {sheriff_name} 归票位】"
    
    speech_iterator = iter(living_agents)
    
    def force_order_selector(last_speaker, groupchat):
        if last_speaker.name == "User_Admin" or last_speaker.name == "法官":
            try: return living_agents[0]
            except: return moderator
        try: return next(speech_iterator)
        except StopIteration: return moderator

    day_group = PrivateThoughtGroupChat(
        agents=[admin_proxy] + living_agents,
        messages=[],
        max_round=len(living_agents) + 1,
        speaker_selection_method=force_order_selector
    )
    manager = autogen.GroupChatManager(day_group, llm_config=config_tongyi)
    
    admin_proxy.initiate_chat(
        manager,
        message=f"【法官】天亮了。{death_announcement} {speech_prefix} 请大家按座位号轮流发言。",
    )

def run_voting(living_agents, admin_proxy, sheriff_name):
    print("\n" + "🗳️ "*15 + "\n>>> 进入投票环节\n" + "🗳️ "*15)
    votes = []
    for voter in living_agents:
        others = [a.name for a in living_agents if a.name != voter.name]
        admin_proxy.initiate_chat(voter, message=f"【系统】请投票放逐。格式：[投票: 玩家_X号]。可选：{', '.join(others)}", max_turns=1)
        target = extract_target(voter.last_message()["content"])
        if target:
            # 警长票算 1.5 票 (简化为逻辑上的处理，这里只做整数统计，若需精确可改)
            # 这里我们简单记录票数，不处理小数
            votes.append(target)
            if voter.name == sheriff_name:
                print(f"👮 警长 {voter.name} 投给了 {target} (此票至关重要)")
                # 简单处理：警长再加一票进去模拟权重
                votes.append(target) 
            else:
                print(f"👉 {voter.name} 投给了 {target}")
    
    if not votes: return None
    return Counter(votes).most_common(1)[0][0]

# ==============================================================================
# 4. 主程序
# ==============================================================================

def run_game(enable_sheriff=False):
    # 初始化日志
    mode_str = "警长局" if enable_sheriff else "标准局"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"{timestamp}_{mode_str}.log"
    original_stdout = sys.stdout
    sys.stdout = Logger(log_filename)
    
    print(f"=== 🐺 狼人杀 Neural Pit v7.0 ({mode_str}) ===")
    
    # 身份分配
    roles = ["狼人"]*3 + ["平民"]*3 + ["预言家", "女巫", "猎人"]
    random.shuffle(roles)
    agents = []
    identity_map = {}
    
    print("\n📜 身份底牌:")
    for i, role in enumerate(roles, 1):
        name = f"玩家_{i}号"
        identity_map[name] = role
        print(f"{name}: {role}")
        if role == "狼人": prompt = WEREWOLF_PROMPT
        elif role == "预言家": prompt = SEER_PROMPT
        elif role == "女巫": prompt = WITCH_PROMPT
        elif role == "猎人": prompt = HUNTER_PROMPT
        else: prompt = VILLAGER_PROMPT
        agents.append(autogen.AssistantAgent(name=name, system_message=prompt, llm_config=config_tongyi))
        
    moderator = autogen.UserProxyAgent("法官", code_execution_config=False, human_input_mode="NEVER")
    admin_proxy = autogen.UserProxyAgent("User_Admin", code_execution_config=False, human_input_mode="NEVER")

    living_agents = agents[:]
    day = 1
    sheriff_name = None # 警长变量

    while True:
        print(f"\n\n========= 第 {day} 天 =========")
        
        # 1. 夜晚
        dead_tonight = run_night_logic(living_agents, identity_map, moderator, admin_proxy)
        
        # 2. 结算
        announce = "昨晚是平安夜。"
        if dead_tonight:
            for d in dead_tonight:
                obj = next((a for a in living_agents if a.name == d), None)
                if obj: living_agents.remove(obj)
            announce = f"昨晚，{', '.join(dead_tonight)} 死亡。"
            print(f"💀 {announce}")
        else:
            print("🕊️ 平安夜")
            
        over, reason = check_victory(living_agents, identity_map)
        if over: print(f"\n🏁 {reason}"); break
        
        # --- 3. 警长竞选 (仅在第一天且开启模式时) ---
        if day == 1 and enable_sheriff:
            sheriff_name = run_sheriff_election(living_agents, admin_proxy)
        
        # 4. 白天发言
        run_day_speech(living_agents, moderator, admin_proxy, announce, sheriff_name)
        
        # 5. 投票 (传入警长名字)
        exiled = run_voting(living_agents, admin_proxy, sheriff_name)
        
        # 警长移交逻辑 (简化：若警长出局，警徽流失)
        if exiled == sheriff_name and sheriff_name is not None:
            print("💔 警长出局，警徽流失（简化处理）。")
            sheriff_name = None

        if exiled:
            print(f"👋 {exiled} 被放逐。")
            obj = next((a for a in living_agents if a.name == exiled), None)
            if obj: living_agents.remove(obj)
            
        over, reason = check_victory(living_agents, identity_map)
        if over: print(f"\n🏁 {reason}"); break
        
        day += 1

    sys.stdout = original_stdout
    print(f"\n✅ 游戏结束。")

# ==============================================================================
# 5. 启动入口 (处理输入)
# ==============================================================================

if __name__ == "__main__":
    while True:
        print("\n" + "="*40)
        print("🐺 AutoGen 狼人杀启动器")
        print("1. 标准局 (无警徽)")
        print("2. 警长局 (有警徽 - 首日竞选)")
        print("0. 退出")
        print("="*40)
        
        choice = input("👉 请输入数字: ").strip()
        
        if choice == "1":
            run_game(enable_sheriff=False)
        elif choice == "2":
            run_game(enable_sheriff=True)
        elif choice == "0":
            print("Bye!")
            break
        else:
            print("❌ 无效输入，请输入 1 或 2。")