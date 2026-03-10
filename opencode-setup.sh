#!/usr/bin/env bash

# opencode-setup.sh
# A script to guide you through setting up OpenCode with Ollama, OpenRouter, and LiteLLM.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   OpenCode Provider Setup            ${NC}"
echo -e "${BLUE} (Ollama, OpenRouter, LiteLLM)        ${NC}"
echo -e "${BLUE}======================================${NC}"

# 1. Collect API Keys
echo -e "\n${BLUE}[1/2] Configuring API Keys${NC}"
read -p "Enter your OpenRouter API Key (leave blank to skip): " OPENROUTER_KEY
read -p "Enter your LiteLLM API Key (leave blank if not needed): " LITELLM_KEY
read -p "Enter your LiteLLM Base URL (default: http://localhost:4000/v1): " LITELLM_URL
LITELLM_URL=${LITELLM_URL:-http://localhost:4000/v1}

# 2. Create Config Directory
CONFIG_DIR="$HOME/.config/opencode"
mkdir -p "$CONFIG_DIR"
CONFIG_FILE="$CONFIG_DIR/config.json"

# 3. Generate config.json
echo -e "\n${BLUE}[2/2] Generating config.json...${NC}"

cat <<EOF > "$CONFIG_FILE"
{
  "\$schema": "https://opencode.ai/config.json",
  "model": "openrouter/google/gemini-2.0-flash-001",
  "small_model": "ollama/qwen3.5:0.8b",
  "provider": {
    "ollama": {
      "name": "Local Ollama",
      "api": "http://localhost:11434/v1",
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "apiKey": "ollama"
      },
      "models": {
        "qwen3.5:27b": {
          "name": "Qwen 3.5 (27B) - Power",
          "limit": { "context": 32768, "output": 4096 }
        },
        "qwen3-coder:latest": {
          "name": "Qwen 3 Coder - Specialist",
          "limit": { "context": 32768, "output": 4096 }
        },
        "qwen3.5:latest": {
          "name": "Qwen 3.5 (7B) - Balanced",
          "limit": { "context": 32768, "output": 4096 }
        },
        "qwen3.5:0.8b": {
          "name": "Qwen 3.5 (0.8B) - Tiny",
          "limit": { "context": 8192, "output": 2048 }
        }
      }
    },
    "openrouter": {
      "name": "OpenRouter",
      "api": "https://openrouter.ai/api/v1",
      "npm": "@openrouter/ai-sdk-provider",
      "options": {
        "apiKey": "{env:OPENROUTER_API_KEY}"
      },
      "models": {
        "google/gemini-2.0-flash-001": {
          "name": "Gemini 2.0 Flash (Fastest)",
          "limit": { "context": 1000000, "output": 8192 }
        },
        "deepseek/deepseek-chat": {
          "name": "DeepSeek V3 (Cheap & Smart)",
          "limit": { "context": 64000, "output": 4096 }
        }
      }
    },
    "litellm": {
      "name": "LiteLLM Proxy",
      "api": "$LITELLM_URL",
      "npm": "@ai-sdk/openai-compatible",
      "options": {
        "apiKey": "{env:LITELLM_API_KEY}"
      },
      "models": {
        "gpt-5": {
          "name": "LiteLLM - GPT-5 (Proxy)",
          "limit": { "context": 128000, "output": 4096 }
        },
        "claude-3-5-sonnet": {
          "name": "LiteLLM - Claude 3.5 (Proxy)",
          "limit": { "context": 2000000, "output": 8192 }
        }
      }
    }
  },
  "agent": {
    "build": {
      "model": "openrouter/google/gemini-2.0-flash-001",
      "temperature": 0.1
    },
    "explore": {
      "model": "ollama/qwen3.5:latest",
      "temperature": 0
    }
  }
}
EOF

echo -e "${GREEN}Config saved to $CONFIG_FILE${NC}"

# 4. Handle Environment Variables
echo -e "\n${BLUE}Finalizing Setup...${NC}"

SHELL_RC=""
case "$SHELL" in
    */zsh) SHELL_RC="$HOME/.zshrc" ;;
    */bash) SHELL_RC="$HOME/.bashrc" ;;
    *) SHELL_RC="$HOME/.profile" ;;
esac

# Function to add/update env var
update_env() {
    local key=$1
    local val=$2
    if [ -n "$val" ]; then
        if grep -q "$key" "$SHELL_RC"; then
            sed -i '' "s/export $key=.*/export $key=\"$val\"/" "$SHELL_RC" 2>/dev/null || \
            sed -i "s/export $key=.*/export $key=\"$val\"/" "$SHELL_RC"
            echo -e "${GREEN}Updated $key in $SHELL_RC${NC}"
        else
            echo "export $key=\"$val\"" >> "$SHELL_RC"
            echo -e "${GREEN}Added $key to $SHELL_RC${NC}"
        fi
        export "$key"="$val"
    fi
}

echo -e "\n# OpenCode" >> "$SHELL_RC"
update_env "OPENROUTER_API_KEY" "$OPENROUTER_KEY"
update_env "LITELLM_API_KEY" "$LITELLM_KEY"

echo -e "\n${BLUE}======================================${NC}"
echo -e "${GREEN}   Setup Complete!                    ${NC}"
echo -e "${BLUE}======================================${NC}"
echo -e "To apply changes to your current terminal, run:"
echo -e "${BLUE}source $SHELL_RC${NC}"
echo -e "\nThen launch OpenCode:"
echo -e "${BLUE}opencode${NC}"
echo -e "\nTips:"
echo -e "- Use ${BLUE}ctrl+x m${NC} in the TUI to switch between providers."
echo -e "- LiteLLM models are mapped to ${BLUE}litellm/gpt-5${NC} and ${BLUE}litellm/claude-3-5-sonnet${NC} by default."
