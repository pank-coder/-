import httpx

import config


async def chat_completion(m, t=None):
    p = {"model": config.LLM_MODEL, "messages": m}
    if t:
        p["tools"] = t
        p["tool_choice"] = "auto"
    h = {"Authorization": "Bearer " + config.LLM_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(config.LLM_URL, headers=h, json=p)
    if r.status_code != 200:
        print("LLM error: " + str(r.status_code) + " " + r.text)
        raise RuntimeError("LLM request failed")
    return r.json()["choices"][0]["message"]
