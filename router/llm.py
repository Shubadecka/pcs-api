from fastapi import APIRouter, HTTPException
from typing import Optional
import lmstudio as lms  # type: ignore

from .schema import LLMResponseRequest, LLMResponseResponse

router = APIRouter()

@router.post("/response", response_model=LLMResponseResponse)
async def get_llm_response(request: LLMResponseRequest):
    """Gets a response from the LLM based on the conversation history."""    
    try:
        with lms.Client("localhost:1446") as client:
            model = client.llm.model(request.model, config={"contextLength": 71000})
            if request.conversation[0].role == "system":
                sys_prompt = request.conversation[0].content
            else:
                sys_prompt = ""
            chat = lms.Chat(sys_prompt)
            for message in request.conversation:
                if message.role == "user":
                    chat.add_user_message(message.content)
                elif message.role == "assistant":
                    chat.add_assistant_message(message.content)
                else:
                    raise HTTPException(status_code=400, detail=f"Invalid message role: {message.role}")
            response = str(model.respond(chat)).strip()
            if "</think>" in response:
                response = response.split("</think>")[1].strip()
            return LLMResponseResponse(
                success=True,
                message="Success",
                response=response
            )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise e
        raise HTTPException(status_code=500, detail=f"Error getting LLM response: {str(e)}")
