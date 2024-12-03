# from langchain_huggingface import HuggingFaceEndpoint
# import os

# async def HuggingFaceAPI(prompt, model):
#     llm = HuggingFaceEndpoint(
#         repo_id=model,
#         temperature=0.5,
#         huggingfacehub_api_token=os.environ.get("HF_ACCESS_TOKEN"),
#     )
#     return llm.invoke(prompt)
