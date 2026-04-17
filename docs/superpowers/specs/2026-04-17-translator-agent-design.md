# 2026-04-17 Built-in Translator Agent Design

## 1. Overview
Add a built-in translator agent to Yue, providing professional bilingual translation between Chinese and English with a focus on technical accuracy and format preservation.

## 2. Goals
- Provide a dedicated agent for English-to-Chinese and Chinese-to-English translation.
- Maintain professional terminology in the original language while providing translations.
- Preserve all Markdown formatting (code blocks, links, etc.).
- Deliver a seamless, "plug-and-play" experience for all users.

## 3. Design
### 3.1. Agent Configuration
- **ID**: `builtin-translator`
- **Name**: `双语翻译专家 (Bilingual Translator)`
- **Model**: `deepseek-reasoner` (preferred for its reasoning capabilities and handling of complex sentence structures)
- **Tools**: None (focusing on lightweight and fast response)

### 3.2. System Prompt Design
The system prompt will define the agent as a professional translator with the following core instructions:
- **Language Detection**: Automatically detect whether the input is Chinese or English.
- **Terminology Handling**: For technical terms, use the format `Translation (Original Term)` or `Original Term (Translation)` depending on context.
- **Format Preservation**: Strictly maintain Markdown syntax, including headers, lists, code blocks, math formulas, and links.
- **Quality Standard**: Aim for "Faithfulness, Expressiveness, and Elegance" (信达雅), avoiding literal or robotic translations.
- **Tone**: Professional and objective.

## 4. Implementation Plan
1. **Backend Integration**:
   - Update `backend/app/services/agent_store.py`.
   - Implement `_builtin_translator_agent()` method returning the `AgentConfig`.
   - Register the new agent in `_builtin_agents()` list.
2. **Verification**:
   - Verify the agent is automatically added to `agents.json` on server startup.
   - Test translation capabilities through integration tests or manual verification.

## 5. Security and Performance
- **Security**: No tool access minimizes potential security risks.
- **Performance**: High performance due to no external tool calls and optimized reasoning model.
