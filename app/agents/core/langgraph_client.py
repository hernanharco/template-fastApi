from langgraph_sdk import get_client

# Esto encapsula toda la comunicación con LangGraph.

class LangGraphClient:

    def __init__(self, url: str):
        self.client = get_client(url=url)

    async def ensure_thread(self, thread_id: str):

        try:
            await self.client.threads.get(thread_id)
        except Exception:
            await self.client.threads.create(thread_id=thread_id)

    async def run_agent(self, thread_id: str, assistant_id: str, payload: dict):

        await self.client.runs.wait(
            thread_id=thread_id,
            assistant_id=assistant_id,
            input=payload,
        )

        return await self.client.threads.get_state(thread_id)