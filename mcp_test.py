# hada_client.py
import asyncio, json
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ─── Configura tu LLM local ───────────────────────────────────────────────────
# LM Studio:  base_url="http://localhost:1234/v1"
# Ollama:     base_url="http://localhost:11434/v1"
# llama.cpp:  base_url="http://localhost:8080/v1"
llm = AsyncOpenAI(
    base_url="http://localhost:8000/v1",
    api_key="no-key"  # LM Studio/Ollama no validan la key, pero la necesita el SDK
)
MODEL = "Hoshiku/HadaAI"  # el modelo que tengas cargado

SERVER = StdioServerParameters(command="python", args=["memory_server.py"])

# ─── Convierte tools MCP → formato OpenAI ────────────────────────────────────
def mcp_tools_to_openai(mcp_tools) -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema,
            }
        }
        for t in mcp_tools
    ]

# ─── Bucle principal: LLM + MCP ──────────────────────────────────────────────
async def chat(user_input: str, session: ClientSession, tools_openai: list) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "Eres HadaAI, una asistente personal. "
                "Tienes acceso a una memoria persistente del usuario. "
                "Úsala para guardar información importante y consultar contexto previo."
            )
        },
        {"role": "user", "content": user_input}
    ]

    # Bucle: el LLM puede hacer múltiples tool calls seguidas
    while True:
        response = await llm.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools_openai,
            tool_choice="auto"
        )
        msg = response.choices[0].message

        # Si no hay tool call → respuesta final
        if not msg.tool_calls:
            return msg.content

        # Hay tool calls → ejecutarlas en el MCP Server
        messages.append(msg)  # añade el mensaje del LLM con los tool_calls

        for tc in msg.tool_calls:
            tool_name = tc.function.name
            tool_args = json.loads(tc.function.arguments)

            print(f"  🔧 Llamando tool: {tool_name}({tool_args})")

            result = await session.call_tool(tool_name, tool_args)
            tool_output = result.content[0].text

            # Devuelve el resultado al LLM
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_output
            })

# ─── Entry point ─────────────────────────────────────────────────────────────
async def main():
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Obtener tools del servidor MCP y convertirlas
            mcp_tools = (await session.list_tools()).tools
            tools_openai = mcp_tools_to_openai(mcp_tools)
            print(f"✅ {len(tools_openai)} tools cargadas del servidor MCP\n")

            # Loop de conversación
            print("HadaAI lista. Escribe 'salir' para terminar.\n")
            while True:
                user_input = input("Tú: ").strip()
                if user_input.lower() in ("salir", "exit", "quit"):
                    break
                if not user_input:
                    continue

                response = await chat(user_input, session, tools_openai)
                print(f"Hada: {response}\n")

asyncio.run(main())