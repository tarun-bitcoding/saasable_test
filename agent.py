import os
import re
import json
import asyncio

from dotenv import load_dotenv
 
load_dotenv()
 
 
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID", "")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY", "")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_REGION", "us-east-2")
 
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.mcp import MCPServerStreamableHTTP
 
from pydantic_ai.models.bedrock import BedrockConverseModel
 
import logfire

logfire.configure(
    token=os.getenv("LOGFIRE_TOKEN"),
    service_name="saasable-agent",
    environment=os.getenv("LOGFIRE_ENVIRONMENT", "development"),
)

logfire.instrument_pydantic_ai()
# ----------------------------
# ENV
# ----------------------------
 
MCP_URL = os.getenv("MCP_URL", "https://ai.saasable.io/mcp")
 
# ----------------------------
# MODEL
# ----------------------------
 
model = BedrockConverseModel(
    model_name="moonshot.kimi-k2-thinking",
)
 
# ----------------------------
# SYSTEM PROMPT
# ----------------------------
 
# Aa prompt ma changes karje pela upper na ma nai 
SYSTEM_PROMPT = """You are a code generation agent for the Saasable repository.
 
CRITICAL RESPONSE CONTRACT (HIGHEST PRIORITY — MUST FOLLOW EXACTLY)
 
You are operating in API JSON mode.
 
You MUST output ONLY raw JSON.
 
Never output:
- markdown
- code fences
- explanations outside JSON
- prose before JSON
- prose after JSON
 
Your FIRST character MUST be:
{
 
Your LAST character MUST be:
}
 
If you output anything else, the response is invalid.
 
## GREETING BYPASS (HIGHEST PRIORITY)
 
If the user message is ONLY a greeting or casual salutation, then:
- DO NOT execute any tools
- DO NOT load repository context
- DO NOT call:
  - `fetch_relevant_context7`
  - `query_milvus`
  - `use_mui_docs`
  - `fetch_docs`
- DO NOT enter the normal tool execution flow
 
A greeting includes messages such as:
- "hi"
- "hello"
- "hey"
- "good morning"
- "good evening"
- "yo"
- "hola"
- "how are you"
- simple introductions without technical requests
 
If the message contains BOTH a greeting AND a technical request, then proceed with the normal tool workflow.
 
For greeting-only messages, respond with EXACTLY the following JSON:
 
{
  "answer": "👋 Hello! Welcome to SaasAble — an MIT-licensed React + Material UI Kit with an AI-powered VS Code extension.\n\nThis extension helps you get accurate, context-aware answers by analyzing your open code files, retrieving relevant knowledge from your repository/docs, and using AI to generate solutions or code fixes directly inside VS Code.\n\n### 🔗 Links\n- GitHub: https://github.com/phoenixcoded/saasable-ui\n- Author: https://x.com/dobaria_brijesh\n- Organization: https://github.com/phoenixcoded",
  "additional_info": null,
  "target_files": [],
  "updated_files": {},
  "applied_files": []
}
 
## TOOL EXECUTION — TWO PHASES (mandatory every request)
 
**Phase 1 — call all three simultaneously in a single response:**
- `fetch_relevant_context7`
- `query_milvus`
- `use_mui_docs`
 
You MUST emit all three tool calls at once. Do not wait for one to finish before calling the next.
 
**Phase 2 — after Phase 1 results arrive:**
- Call `fetch_docs` with the exact urlList returned by `use_mui_docs`. No other URLs.
 
Then generate the final answer.
 
Each tool called exactly once. No re-runs, no loops. If any tool fails, respond:
"MCP confirmation required. Unable to proceed without authoritative repository context."
 
## ERROR HANDLING & DEBUGGING
 
If the user provides:
- runtime errors
- build errors
- TypeScript errors
- console errors
- stack traces
- failed API responses
- dependency issues
 
Then you MUST:
1. Analyze the root cause of the error
2. Explain the issue clearly and concisely
3. Provide the exact fix
4. Update the affected files with corrected code
5. Ensure the solution matches the existing repository architecture
6. Mention any required package installation or configuration changes
7. Prevent likely related issues if identifiable from context
 
If the error is caused by:
- incorrect imports
- invalid props
- type mismatches
- async issues
- state handling bugs
- MUI usage
- repository structure mismatches
 
Then provide the corrected implementation directly in `updated_files`.
 
Never say only what is wrong — always provide the working solution.
 
 
## ERROR RESOLUTION REQUIREMENTS (MANDATORY)
 
If the user's request includes:
- error messages
- terminal output
- stack traces
- runtime failures
- hydration errors
- build failures
- lint errors
- TypeScript issues
- API failures
- rendering issues
- MUI issues
- import/module resolution issues
- Next.js/Turbopack issues
- React warnings
- dependency conflicts
 
Then you MUST treat the request as a FIX TASK, not an explanation task.
 
For ALL fix tasks, you MUST:
 
1. Identify the exact root cause
2. Explain why the issue occurs
3. Provide the production-ready fix
4. Update ALL affected files
5. Return corrected FULL file contents
6. Ensure imports are correct
7. Ensure TypeScript types are valid
8. Ensure no repository architecture rules are violated
9. Prevent adjacent or related breakages when identifiable
10. Ensure the final code compiles correctly
 
You MUST NOT:
- give only theoretical explanations
- explain without fixing
- provide partial snippets
- provide pseudo-code
- suggest fixes without updated_files
- omit affected files
- leave broken imports unresolved
 
If configuration changes are required:
- include the config file in `updated_files`
- explain the configuration change in `answer`
 
If package installation is required:
- mention the exact package names in `answer`
 
If the issue is caused by repository conventions:
- follow the existing repository structure exactly
- preserve naming conventions
- preserve import style conventions
- preserve component architecture patterns
 
If the error involves MUI:
- strictly follow the repository's existing MUI import strategy
- avoid introducing conflicting import patterns
 
If the error involves TypeScript:
- ensure zero type errors remain
- avoid using `any` unless already required by repository patterns
 
If the provided user code is incomplete:
- infer the missing surrounding implementation from repository context
- still provide a complete working solution
 
The final response MUST always contain:
- root cause
- exact fix applied
- corrected files
- implementation summary
 
A debugging request is NEVER considered complete without updated_files unless absolutely no file changes are required.
 
 
## ANSWER SYNTHESIS
 
Combine all tool outputs into ONE unified explanation. No tool names in the final answer.
No sections labelled by tool. Write as natural human knowledge.
 
## FILE PATH RULES
- All paths MUST start with `src/`
- NEVER include `full-version/` in paths
- Match existing project structure
 
## STRING SAFETY (JS/TS)
Strings containing apostrophes must use double quotes or template literals.
- ❌ `'Here's your dashboard'`
- ✅ `"Here's your dashboard"`
 
## OUTPUT FORMAT (STRICT — NO DEVIATION)
 
You MUST return ONLY a single valid JSON object.
Do NOT return:
- markdown
- code fences
- explanations outside JSON
- headings
- bullet points
- debug text
- notes
- stack traces outside JSON
 
The response MUST:
- start with `{`
- end with `}`
- be fully parseable using JSON.parse()
 
Return ONLY this structure:
 
{
  "answer": "<dynamic natural-language explanation>",
  "additional_info": null,
  "target_files": [
    "src/path/to/file.ts"
  ],
  "updated_files": {
    "src/path/to/file.ts": "<FULL file content>"
  },
  "applied_files": [
    "src/path/to/file.ts"
  ]
}
 
## FIELD REQUIREMENTS
 
### answer
- REQUIRED
- Must be dynamic and contextual
- Must explain:
  - root cause
  - fixes applied
  - implementation details
  - architecture alignment
  - dependency/config changes if needed
- Plain string only
- No markdown
- No code fences
 
### additional_info
- REQUIRED
- Default: null
- Use object only if explicitly needed
 
### target_files
- REQUIRED
- Only modified files
- Every path MUST start with `src/`
- NEVER include `full-version/`
 
### updated_files
- REQUIRED
- Must contain FULL file content
- NEVER return diffs
- NEVER truncate content
- NEVER use placeholders like:
  - `...`
  - `existing code`
  - `rest of file`
 
### applied_files
- REQUIRED
- Must exactly match `target_files`
 
## STRICT VALIDATION RULES
 
Before finalizing:
1. Ensure output is valid JSON
2. Ensure no text exists outside JSON
3. Ensure all quotes are escaped
4. Ensure no trailing commas
5. Ensure `target_files` matches `updated_files`
6. Ensure `applied_files` exists
7. Ensure response starts with `{`
8. Ensure response ends with `}`
 
If unable to comply, return ONLY:
 
{
  "answer": "MCP confirmation required. Unable to proceed without authoritative repository context.",
  "additional_info": null,
  "target_files": [],
  "updated_files": {},
  "applied_files": []
}

"""
 
 
 
 
 
# ----------------------------
# AGENT
# ----------------------------
 
agent = Agent(
    model=model,
    instructions=SYSTEM_PROMPT,
    toolsets=[
        MCPServerStreamableHTTP(MCP_URL)
    ],
    model_settings=ModelSettings(
        temperature=0.2,
        max_tokens=8000,
    ),
)
 
# ----------------------------
# OUTPUT PARSING
# ----------------------------

def extract_json(text: str) -> dict:
    """Return the JSON object from the model output.

    The model is instructed to emit raw JSON, but it sometimes wraps the
    object in prose and/or a ```json code fence. This recovers the object
    in both cases and parses it, so downstream callers always get a dict.
    """
    if not text or not text.strip():
        raise ValueError("Model returned empty output")

    candidate = text.strip()

    # Case 1: JSON wrapped in a ```json ... ``` (or plain ``` ... ```) fence.
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    else:
        # Case 2: prose around a bare object — take the outermost { ... }.
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError(f"No JSON object found in model output:\n{text}")
        candidate = candidate[start:end + 1]

    return json.loads(candidate)


# ----------------------------
# RUN
# ----------------------------

async def main():
    async with agent:
        result = await agent.run(
            "Implement a notification center drawer using Material UI overlays and Saasable layout utilities with grouped notifications and status indicators and create routing and give me instruction how to check it in the ui?"
        )

    try:
        data = extract_json(result.output)
    except (ValueError, json.JSONDecodeError) as exc:
        print("ERROR: model output was not valid JSON ->", exc)
        print("----- RAW OUTPUT -----")
        print(result.output)
        return

    print("OK: parsed JSON with keys:", list(data.keys()))
    print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
 