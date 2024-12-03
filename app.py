import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from db import initialize_db
from boto3.dynamodb.conditions import Key
from fastapi import FastAPI, Query, Request,HTTPException,UploadFile
from airport_search import airport_search
from fastapi.responses import JSONResponse
from vadersentiment import TextInput, analyze_sentiment as vader_analyze_sentiment
from prompts import AICodeTransalatorPrompt, Translate, Summarizer,truncate_to_max_words
from groqAPI import groqAPI
from prompts import generate_prompt,ResumeContent
from website_summarizer import SummarizeRequest, fetch_webpage_content, summarize_and_analyze
from rechargeportal import recharge_service, check_transaction_status_service, get_services
from wrapper import get_ip_info
from typing import Optional
from Utils import (
    log_request,
    update_response,
    update_model,
    check_limits,
    format_transcript,
)
from uuid import uuid4
from ppp import get_ppp_data
from fastapi.encoders import jsonable_encoder
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube
from routes import get_all_routes_function 
from currency_data import fetch_country_data
from get_ip import get_routes_and_whitelist
from starlette.responses import RedirectResponse
from url_redirect import (
    generate_short_key,
    store_url,
    get_original_url,
    log_visitor,
    get_analytics,
    URLRequest,
)
from geoUtils import get_country_from_ip
import os
from pdfsummarizer import extract_text_from_pdf,extract_text_from_csv,extract_text_from_xlsx
app = FastAPI(
    docs_url="/",
    redoc_url=None,
    title="TT API Hub",
    summary="Collection of API end points to use in real time",
    version="1.0.0",
    contact={
        "name": "Support",
        "email": "support@tackletechies.com",
    },
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
headers = {
        "Access-Control-Allow-Origin": "*",  # Allow all origins
        "Access-Control-Allow-Methods": "*",  # Allow all HTTP methods
        "Access-Control-Allow-Headers": "*",  # Allow all headers
}
@app.middleware("http")
async def middle(request: Request, call_next):
    path = request.scope["path"]
    print(path)
    if "/api/" in path and request.method != "OPTIONS":
        api_key = request.headers.get("X-APIKey")
        pricing_header = request.headers.get("X-Pricing")

        
        if not api_key:
            return JSONResponse(content={"error": "API Key is missing"}, status_code=401, headers=headers)
        if not pricing_header:
            return JSONResponse(content={"error": "Pricing is missing"}, status_code=401, headers=headers)

        ddb = initialize_db()
        table_users = ddb.Table("Users_dev")
        table_apicodes = ddb.Table("APICodes_dev")
        user_id = None

        if api_key.startswith("UID"):
            user_id = api_key[3:]  
            try:
                response = table_users.query(
                    IndexName="UserIdIndex",
                    KeyConditionExpression=Key('UserId').eq(user_id)
                )
            except Exception as e:
                return JSONResponse(content={"error": "Error fetching user data"}, status_code=500, headers=headers)

            
            if response["Count"] == 0:
                return JSONResponse(content={"error": "Not a valid User Id"}, status_code=401, headers=headers)

            user_item = response["Items"][0]

            if request.client.host != user_item.get("IPAddress"):
             return JSONResponse(content={"error": "IP address does not match"}, status_code=401, headers=headers)

            
            check_limit = await check_limits(email=user_item['Email'], pricing=pricing_header, user_data=user_item)

        else:
            
            api_data = table_apicodes.get_item(Key={"key": api_key})
            if "Item" not in api_data:
                return JSONResponse(content={"error": "Not a valid API Key"}, status_code=401, headers=headers)

            item = api_data["Item"]

            
            if request.client.host not in item.get("WhiteList", []):
                return JSONResponse(content={"error": "Your IP is not whitelisted"}, status_code=401, headers=headers)
            if path not in item.get("Routes", []):
                return JSONResponse(content={"error": "You are not authorized to use this route"}, status_code=401, headers=headers)

            user_id = item.get("UserId")

           
            user_response = table_users.query(
                IndexName="UserIdIndex",
                KeyConditionExpression=Key('UserId').eq(user_id)
            )
            user_item = user_response["Items"][0] if user_response["Count"] > 0 else None

            
            if not user_item:
                return JSONResponse(content={"error": "User not found."}, status_code=404, headers=headers)

            check_limit = await check_limits(email=user_item['Email'], pricing=pricing_header, user_data=user_item)

        
        if check_limit and "error" in check_limit:
            return JSONResponse(content={"error": str(check_limit["error"])}, status_code=500, headers=headers)

        request.state.LogId = str(uuid4())
        await log_request(request)
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response
        
    elif "/api/" in path:
        response = JSONResponse(content={}, headers=headers)  
        return response

    response = await call_next(request)
    return response


@app.get("/api/airport-search")
async def search_airport(param: str = Query(None, min_length=2)):
    """
    Return the List of airports Code/Name matching with param in City, Country and Airport Name
    """
    return await airport_search(param)


@app.post("/api/analyze")
async def analyze_sentiment(input: TextInput):
    """
    Analyze the sentiment of a list of texts.

    Each text in the list will be analyzed and the sentiment scores will be returned.
    The scores include 'compound', 'positive', 'neutral', and 'negative'.

    - texts: A list of strings to be analyzed for sentiment.
    """
    return await vader_analyze_sentiment(input)

@app.post("/api/codetranslate")
async def code_translate(input: Translate, request: Request):
    """
    Translate the code from one programming language to another programming language
    or natural language to any programming language
    or any programming language to nature language ( explanation )

    input
    -
    """
    model = await update_model(request.state.LogId, request.headers["X-Pricing"])
    input.inputCode = truncate_to_max_words(input.inputCode, 2500)
    prompt = AICodeTransalatorPrompt(input)
    return await groqAPI(prompt, model)


@app.get("/api/ppp")
async def get_ppp(origin: str, destination: str, origin_amount: float):
    """
    Calculate the purchasing power parity (PPP) between two countries.

    - origin - origin country initials
    - destination - destination country initials
    - originAmount - origin country amount which need to be convert
    """
    result = get_ppp_data(origin, destination, origin_amount)
    return result


@app.get("/api/youtube")
async def youtube_summariser(
    request: Request,
    video_id: str = Query(None, min_length=2),
    translate: str = Query(None, min_length=2),
):
    """
    Youtube summariser which provides the summary, transcripts and fact checking with age appropriate for the content

    - url - youtube url link
    - translate - translate the transcripts with specified language if available
    """
    try:
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        youtube_transcript = YouTubeTranscriptApi.get_transcript(video_id=video_id)
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        translated_transcript = []
        for transcript in transcript_list:
            if transcript.is_translatable == True and any(
                x
                for x in transcript.translation_languages
                if "language_code" in x and x["language_code"] == translate
            ):
                translated_transcript = transcript.translate(translate).fetch()
        model = await update_model(request.state.LogId, request.headers["X-Pricing"])
        transcript = ' '.join(format_transcript(youtube_transcript).split()[:5000])
        prompt = Summarizer(transcript, "YouTube")
        summary = await groqAPI(prompt, model)
        return JSONResponse(
            content={
                "videoInfo": {
                    "author": yt.author,
                    "channelId": yt.channel_id,
                    "channelUrl": yt.channel_url,
                    "description": yt.description,
                    "length": yt.length,
                    "thumbnailUrl": yt.thumbnail_url,
                },
                "Summary": summary,
                "transcript": youtube_transcript,
                "translatedTranscript": translated_transcript,
            },
            status_code=200,
        )
    except Exception as err:
        print(err)
        return JSONResponse(
            content={"error": str(err)},
            youtube_transcript={youtube_transcript},
            status_code=500,
        )

@app.get("/api/routes")
async def get_all_routes():
    """Retrieve all unique routes from the DynamoDB table."""
    return await get_all_routes_function()

@app.post("/api/website_summarizer")
async def summarize_webpage(request: Request, body: SummarizeRequest):
    """
    Summarize the content of a given webpage, provide a sentiment analysis score, 
    and perform basic fact-checking.
    """
    url_to_summarize = str(body.url)
    combined_content = ""
    max_words = 5000

    try:
       
        text_content = fetch_webpage_content(url_to_summarize)
        combined_content = text_content[:max_words]
        
        if combined_content.strip():
            
            model = await update_model(request.state.LogId, request.headers.get("X-Pricing", "default"))
            analysis_results = await summarize_and_analyze(combined_content, model)
            
           
            summaries = {
                "summary": analysis_results.get("summary", "No summary available."),
                "sentiment_score": analysis_results.get("sentiment_score", "No sentiment score available."),
                "fact_check_result": analysis_results.get("fact_check_result", "No fact-checking available.")
            }
        else:
            summaries = {"summary": "No meaningful content extracted."}

    except Exception as e:
        summaries = {"error": f"Error: {e}"}

    return JSONResponse(content={"url": url_to_summarize, "summaries": summaries})
    
@app.get("/api/country-data")
async def get_country_data():
    """Fetch country data from the REST Countries API"""
    country_data = await fetch_country_data()
    return country_data

@app.get("/api/get_ip")
async def get_whitelist_and_routes(
    apikey: Optional[str] = Query(None),
    userid: Optional[str] = Query(None)
):
    """
    Retrieve the WhiteList and Routes for the given API key or UserId.
    """
    result = await get_routes_and_whitelist(apikey=apikey, userid=userid)
    return result

@app.get("/api/services")
async def get_services_endpoint():
    """
    Return the list of services available.
    """
    return get_services()

@app.post("/api/recharge")
async def recharge_endpoint(request: Request):
    """
    Process a recharge request.
    """
    return await recharge_service(request)

@app.post("/api/checkTransactionStatus")
async def check_transaction_status_endpoint(request: Request):
    """
    Check the status of a transaction as success / failure
    """
    return await check_transaction_status_service(request)

@app.get("/api/ipinfo")
async def ip_info_handler(request: Request):
    """Get the GeoLocation details of the request"""
    return await get_ip_info(request)

@app.post("/api/ats_score")
async def analyze_resume(request: Request, resume: ResumeContent):
    """
    Analyze the resume content by passing it to the AI model via groqAPI.
    """    
    model = await update_model(request.state.LogId, request.headers["X-Pricing"]) 
    if not resume.content or not resume.content.strip():
        return {"error": "Invalid resume content, unable to generate a prompt."}
    messages = generate_prompt(resume.content)      
    try:
        ai_response = await groqAPI(messages=messages, model=model)
    except Exception as e:
        
        return {"error": "Failed to process the resume with AI model."}
    return {
        "ATS_Score_And_Improvements": ai_response
    }

@app.post("/api/shorten_url")
async def shorten_url(request: Request, url_request: URLRequest):
    """
    Shorten a URL and return the short URL.
    """
    long_url = url_request.long_url.strip()
    if not long_url:
        return {"error": "Invalid URL, unable to shorten."}
    short_key = generate_short_key(long_url)
    store_url(long_url, short_key)
    base_url = os.getenv("BASE_URL", f"{request.url.scheme}://{request.client.host}:{request.url.port}")
    short_url = f"{base_url}/{short_key}" 
    return {"short_url": short_url}


@app.get("/{short_key}")
async def redirect_to_url(short_key: str, request: Request):
    """
    Redirect to the original URL and collect analytics data.
    """
    original_url = get_original_url(short_key)
    if not original_url:
       return {"error":"Short URL not found."}

  
    visitor_ip = request.client.host
    visitor_country = get_country_from_ip(visitor_ip) 
    
    log_visitor(short_key, visitor_ip, visitor_country)

    return RedirectResponse(original_url)


@app.get("/api/analytics/{short_key}")
async def get_url_analytics(short_key: str):
    """
    Retrieve analytics data for the given short key.
    """
    analytics = get_analytics(short_key)
    if not analytics:
        
        return {"error": "No analytics found for this short URL."}
    return {"analytics": analytics}


@app.post("/api/summarize-pdf/")
async def summarize_pdf(file: UploadFile, request: Request):
    """
    Reviews and summarizes legal documents using AI.
    """
    # Fetch model details using your custom function
    model = await update_model(request.state.LogId, request.headers.get("X-Pricing")) 
    
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF.")
    
    # Extract text from PDF
    pdf_text = extract_text_from_pdf(file)
    if not pdf_text:
        raise HTTPException(status_code=400, detail="No text found in the PDF.")
    
    # Prepare messages for GroqAPI prompt
    messages = [
        {"role": "system", "content": "You are a legal AI assistant specializing in reviewing and summarizing legal documents."},
        {"role": "user", "content": (
            "The following text is extracted from a legal document. "
            "Please summarize the key points, highlight potential issues, and ensure the content is concise and easy to understand.\n\n"
            f"Document Content:\n{pdf_text}\n\n"
            "Your output should include:\n"
            "1. A brief summary of the document.\n"
            "2. Key points with bullet points.\n"
            "3. Highlighted potential legal issues or ambiguities."
        )}
    ]
    # Call GroqAPI with the prepared prompt
    try:
        summary = await groqAPI(messages, model)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error summarizing PDF: {e}")

@app.post("/api/extract-pdf/")
async def extract_pdf(file: UploadFile):
    """
    Endpoint to extract text from a PDF.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF.")

    # Extract text from PDF
    try:
        pdf_text = extract_text_from_pdf(file)
        return {"extracted_text": pdf_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting PDF text: {e}")
    
if __name__ == "__main__":
    uvicorn.run(app)
