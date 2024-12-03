from fastapi.middleware.cors import CORSMiddleware
from db import initialize_db
from fastapi import FastAPI, Query, Request
from airport_search import airport_search
from fastapi.responses import JSONResponse
from vadersentiment import TextInput, analyze_sentiment as vader_analyze_sentiment
from prompts import AICodeTransalatorPrompt, Translate, Summarizer
from groqAPI import groqAPI
from website_summarizer import SummarizeRequest, fetch_webpage_content, summarize_text, get_internal_links
from Utils import (
    LogRequest,
    updateResponse,
    UpdateModel,
    checkLimits,
    format_transcript,
)
from uuid import uuid4
from ppp import get_ppp_data
from fastapi.encoders import jsonable_encoder
from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube
from routes import get_all_routes_function 
from currency_data import fetch_country_data


app = FastAPI(
    docs_url="/",
    redoc_url=None,
    title="TT API Hub",
    summary="Collection of API end points to use in real time",
    version="1.0.0",
    contact={
        "name": "Support",
        "email": "api-hub@tackletechies.com",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.middleware("http")
async def middle(request: Request, call_next) -> JSONResponse:
    path = request.scope["path"]
    if "/api/" in path and request.method!="OPTIONS":
        if "X-APIKey" in request.headers:
            if "X-Pricing" in request.headers:
                ddb = initialize_db()
                table = ddb.Table("APICodes")
                data = table.get_item(Key={"key": request.headers["X-APIKey"]})
                if (
                    "Item" in data
                    and "WhiteList" in data["Item"]
                    and "Routes" in data["Item"]
                ):
                    if request.client.host in data["Item"]["WhiteList"]:
                        if path in data["Item"]["Routes"]:
                            request.state.LogId = str(uuid4())
                            await LogRequest(request)
                            checkLimit = await checkLimits(request)
                            if checkLimit == True:
                                response = await call_next(request)
                                await updateResponse(request, response)
                                return response
                            else:
                                return JSONResponse(
                                    content={"error": "Daily limit is exceeded"},
                                    status_code=429,
                                )
                        else:
                            return JSONResponse(
                                content={
                                    "error": "You are not authorized to use this route"
                                },
                                status_code=401,
                            )
                    else:
                        return JSONResponse(
                            content={"error": "Your IP is not whitelisted"},
                            status_code=401,
                        )
                else:
                    return JSONResponse(
                        content={"error": "Not a valid API Key"}, status_code=401
                    )
            else:
                return JSONResponse(
                    content={"error": "Pricing is missing"}, status_code=401
                )
        else:
            return JSONResponse(
                content={"error": "API Key is missing"}, status_code=401
            )
    else:
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
    model = await UpdateModel(request.state.LogId, request.headers["X-Pricing"])
    prompt = AICodeTransalatorPrompt(input)
    return await groqAPI(prompt, model)


@app.get("/api/ppp")
async def get_ppp(origin: str, destination: str, originAmount: float):
    """
    Calculate the purchasing power parity (PPP) between two countries.

    - origin - origin country initials
    - destination - destination country initials
    - originAmount - origin country amount which need to be convert
    """
    result = get_ppp_data(origin, destination, originAmount)
    return result


@app.get("/api/youtube")
async def youtube_summariser(
    request: Request,
    videoId: str = Query(None, min_length=2),
    translate: str = Query(None, min_length=2),
):
    """
    Youtube summariser which provides the summary, transcripts and fact checking with age appropriate for the content

    - url - youtube url link
    - translate - translate the transcripts with specified language if available
    """
    try:
        yt = YouTube(f"https://www.youtube.com/watch?v={videoId}")
        youtube_transcript = YouTubeTranscriptApi.get_transcript(video_id=videoId)
        transcript_list = YouTubeTranscriptApi.list_transcripts(videoId)
        translated_transcript = []
        for transcript in transcript_list:
            if transcript.is_translatable == True and any(
                x
                for x in transcript.translation_languages
                if "language_code" in x and x["language_code"] == translate
            ):
                translated_transcript = transcript.translate(translate).fetch()
        model = await UpdateModel(request.state.LogId, request.headers["X-Pricing"])
        Transcript = ' '.join(format_transcript(youtube_transcript).split()[:5000])
        prompt = Summarizer(Transcript, "YouTube")
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
     Summarize the content of a given webpage or all internal links found within the webpage.

    - request: FastAPI Request object to access state and headers.
    - body: SummarizeRequest object containing the URL to summarize and whether to summarize all internal links.    
    """
    summaries = {}
    urls_to_summarize = set()

    
    if body.allRoutes == 1:
        urls_to_summarize = get_internal_links(str(body.url))
    else:
        urls_to_summarize.add(str(body.url))

    combined_content = ""
    max_words = 5000  

    
    for url in urls_to_summarize:
        try:
            text_content = fetch_webpage_content(url)
            combined_content += text_content + " "  

            
            if len(combined_content.split()) > max_words:
                combined_content = ' '.join(combined_content.split()[:max_words])
                break  
        except Exception as e:
            summaries[url] = f"Error while fetching content from {url}: {e}"

   
    try:
        if combined_content.strip(): 
            model = await UpdateModel(request.state.LogId, request.headers.get("X-Pricing", "default"))
            summary = await summarize_text(combined_content, model)
            
            
            for url in urls_to_summarize:
                summaries[url] = summary
        else:
            for url in urls_to_summarize:
                summaries[url] = "No meaningful content extracted."
                
    except Exception as e:
        for url in urls_to_summarize:
            summaries[url] = f"Error while summarizing content: {e}"

    return JSONResponse(content={"summaries": summaries})

@app.get("/api/country-data")
async def get_country_data():
    """Fetch country data from the REST Countries API"""
    country_data = await fetch_country_data()
    return country_data

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
