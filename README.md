# ?? llm-mafia: AutoGen Werewolf Arena

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![AutoGen](https://img.shields.io/badge/Framework-AutoGen-purple)](https://microsoft.github.io/autogen/)
[![Manager](https://img.shields.io/badge/Package_Manager-uv-orange)](https://github.com/astral-sh/uv)

**Neural Pit** is a multi-agent simulation of the classic social deduction game *Werewolf* (Mafia), powered by Microsoft AutoGen.

Unlike standard chatbots, agents in this arena possess a **Dual-Layer Cognition System**: they think privately before they speak. This project demonstrates how to orchestrate heterogeneous LLMs (Qwen, DeepSeek, GPT-4) to engage in deception, logic reasoning, and voting.

## ? Key Features

* **? 9-Player Standard Setup**: Full role configuration including 3 Werewolves, 3 Villagers, Seer, Witch, and Hunter.
* **? Inner Monologue vs. Public Speech**:
    * Agents generate hidden thoughts `(INNER_THOUGHT: ...)` to plan strategy.
    * A custom `GroupChat` layer filters these thoughts from the game history, so other agents only see the `PUBLIC_SPEECH`.
    * Human observers see *everything* (God View).
* **? Heterogeneous Model Support**: Configured to run with **Alibaba Qwen (Tongyi)** by default, with support for OpenAI (GPT-4) and DeepSeek.
* **? Thinking Mode Enabled**: Leverages Qwen's `enable_thinking` parameter for deeper logical reasoning during the game.
* **? Auto-Logging**: Every game session is automatically saved to a timestamped `.log` file for replay analysis.
* **? Modern Tooling**: Built with `uv` for lightning-fast dependency management.

## ?? Installation

This project uses [uv](https://github.com/astral-sh/uv) for package management.

### 1. Clone the repository
```bash
git clone [https://github.com/your-username/neural-pit.git](https://github.com/your-username/neural-pit.git)
cd neural-pit
```

### 2. Install dependencies
```bash
uv sync
```

### 3. Configure Environment
We provide an example environment file `.env.example`. You need to create a `.env` file from it.

**Linux / macOS:**

```bash
cp .env.example .env
```

**Windows (PowerShell):**

```powershell
cp .env.example .env
```

Open the `.env` file and fill in your API keys:

```ini
# Required if using the default config (Qwen)
TONGYI_API_KEY=sk-xxxxxxxxxxxxxxxxx

# Optional (if you switch models in config.py)
OPENAI_API_KEY=sk-proj-xxxxxxxx
DEEPSEEK_API_KEY=sk-xxxxxxxx
```

## ? Usage
Run the simulation with a single command. `uv` will handle the virtual environment automatically.

```bash
uv run main.py
```

You will see the game unfold in the terminal, and a log file (e.g., `2025-12-16_10-00-00.log`) will be created in the current directory.

## ? How It Works
### The Architecture
1. **Agents**: Each player is an `autogen.AssistantAgent` with a specific system prompt defining their role (Wolf, Seer, etc.).
2. **Moderator**: An AI agent acts as the game judge, managing the day/night cycle.
3. **Privacy Layer**: We override the `GroupChat.append()` method. It uses Regex to strip `(INNER_THOUGHT)` content before adding messages to the shared context window.

### Example Output
*What the User (You) sees in logs:*

> **Werewolf_1**: (INNER_THOUGHT: The Seer is suspicious of me. I need to counter-attack.) PUBLIC_SPEECH: I think Player 4 is acting very nervous. He might be a wolf trying to hide!

*What Player 4 (Seer) sees:*

> **Werewolf_1**: I think Player 4 is acting very nervous. He might be a wolf trying to hide!

## ?? Configuration
Check `config.py` to switch models. By default, it uses **Qwen-Plus** with "Thinking" enabled:

```python
config_tongyi = {
    "config_list": [{
        "model": "qwen-plus",
        "api_key": os.environ.get("TONGYI_API_KEY"),
        "base_url": "[https://dashscope.aliyuncs.com/compatible-mode/v1](https://dashscope.aliyuncs.com/compatible-mode/v1)",
        "extra_body": {
            "enable_thinking": True  # Enables Deep Reasoning
        }
    }],
    "temperature": 0.5,
}
```

## ? Contributing
Pull requests are welcome! Feel free to add new roles (Guard, Idiot), improve the Moderator logic, or add a web UI.

## ? License[MIT](https://www.google.com/search?q=LICENSE)