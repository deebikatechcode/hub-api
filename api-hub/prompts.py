from pydantic import BaseModel

class Translate(BaseModel):
    inputLanguage: str
    outputLanguage: str
    inputCode: str


def AICodeTransalatorPrompt(input: Translate) -> list:
    messages = []
    if input.inputLanguage == "Natural Language":
        messages.append(
            {
                "role": "system",
                "content": f"You are an expert programmer in {input.outputLanguage} language. Translate the natural language to {input.outputLanguage} code. You can provide error free improvised code. if any questions is asked outside programming you can say 'Sorry, I don't know'.",
            }
        )
        messages.append(
            {
                "role": "user",
                "content": f"Natural language: {input.inputCode}\n {input.outputLanguage} code:",
            },
        )
    elif input.outputLanguage == "Natural Language":
        messages.append(
            {
                "role": "system",
                "content": f"You are an expert programmer in {input.inputLanguage} language. Translate the {input.inputLanguage} code to natural language in plain English that the average adult could understand. Respond as bullet points starting with -.",
            }
        )
        messages.append(
            {
                "role": "user",
                "content": f"{input.inputLanguage} code:\n {input.inputCode} \n Natural language:",
            },
        )
    else:
        messages.append(
            {
                "role": "system",
                "content": f"You are an expert programmer in both {input.inputLanguage} and {input.outputLanguage} Languages. Translate the {input.inputLanguage} code to {input.outputLanguage} code. You can provide error free improvised code.",
            }
        )
        messages.append(
            {
                "role": "user",
                "content": f"{input.inputLanguage} code: \n {input.inputCode} \n {input.outputLanguage} code:",
            },
        )
    return messages


def AICodeTransalatorPromptFree(input: Translate) -> str:
    if input.inputLanguage == "Natural Language":
        return f"You are an expert programmer in {input.outputLanguage} language. Translate the natural language to {input.outputLanguage} code. You can provide error free improvised code. if any questions is asked outside programming you can say 'Sorry, I don't know'. Natural language: {input.inputCode} \n {input.outputLanguage} code: "
    elif input.outputLanguage == "Natural Language":
        return f"You are an expert programmer in {input.inputLanguage} language. Translate the {input.inputLanguage} code to natural language in plain English that the average adult could understand. Respond as bullet points starting with -. You can provide error free improvised code. if any questions is asked outside programming you can say 'Sorry, I don't know'. {input.inputLanguage} code: {input.inputCode} \n Natural language: "
    else:
        return f"You are an expert programmer in  both {input.inputLanguage}  and {input.outputLanguage} languages. Translate the {input.inputLanguage} code to {input.outputLanguage} code. You can provide error free improvised code. if any questions is asked outside programming you can say 'Sorry, I don't know'. {input.inputLanguage} code: {input.inputCode} \n {input.outputLanguage} code: "


def Summarizer(DescribeText, feature):
    messages = []

    if feature == "YouTube":
        messages.append(
            {
                "role": "system",
                "content": f"Your task is to generate a short summary of a youtube transacript. \
                             Please ensure the summary should be comprehensive and clear understanding of the transcript. \
                             Highlights the key points and important moments with fact check (only do if you're 100% sure) in bullet points seperated with - . \
                             Rate the content from which age they can watch. \
                             Avoid any sponsorships or brand names.",
            }
        )
        messages.append(
            {
                "role": "user",
                "content": f"Transcript: {DescribeText}",
            },
        )
    return messages


def SummarizerFree(DescribeText, feature):
    if feature == "YouTube":
        return (
            f"Your task is to generate a short summary of a youtube transacript. \
                             Please ensure the summary should be comprehensive and clear understanding of the transcript. \
                             Highlights the key points and important moments with fact check (only do if you're 100% sure) in bullet points seperated with - . \
                             Rate the content from which age they can watch. \
                             Avoid any sponsorships or brand names. Transcript: {DescribeText}",
        )
