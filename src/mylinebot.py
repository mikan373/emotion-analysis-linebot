"""
オウム返し Line Bot
"""

import os

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage
)

import boto3

handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))

client = boto3.client('rekognition')


def lambda_handler(event, context):
    headers = event["headers"]
    body = event["body"]

    # get X-Line-Signature header value
    signature = headers['x-line-signature']

    # handle webhook body
    handler.handle(body, signature)

    return {"statusCode": 200, "body": "OK"}


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """ TextMessage handler """
    input_text = event.message.text

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f'{input_text} だよね'))


@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    # ユーザーから送られてきた画像を一時ファイルとして保存
    message_content = line_bot_api.get_message_content(event.message.id)
    file_path = "/tmp/sent-image.jpg"
    with open(file_path, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)

    # Rekognitionで感情分析
    with open(file_path, 'rb') as fd:
        sent_image_binary = fd.read()
        response = client.detect_faces(
            Image={"Bytes": sent_image_binary},
            Attributes=['ALL']
        )

    total_emotion = {}

    for detail in response["FaceDetails"]:
        if most_confident_emotion(detail["Emotions"]) not in total_emotion.keys():
            total_emotion[most_confident_emotion(detail["Emotions"])] = 1
        else:
            total_emotion[most_confident_emotion(detail["Emotions"])] += 1

    # 返答を送信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=list_all_emotions(total_emotion)))

    # file_pathの画像を削除
    os.remove(file_path)


def most_confident_emotion(emotions):
    max_conf = 0
    result = ""
    for e in emotions:
        if max_conf < e["Confidence"]:
            max_conf = e["Confidence"]
            result = e["Type"]
    return result


def list_all_emotions(total_emotion):
    phrases = {
        'HAPPY': "Happy 😊",
        'DISGUSTED': "Disgusted 🤢",
        'SAD': "Sad 😢",
        'ANGRY': "Angry 😡",
        'CONFUSED': "Confused 😵‍💫",
        'SURPRISED': "Surprised 😲",
        'CALM': "Calm 😌",
        'UNKNOWN': "Unknown ❓",
        'FEAR': "Fear 😨"
    }

    strings = []

    for emotion in total_emotion:
        # In case the emotion is not in above dictionary, just say text
        phrase = phrases.get(emotion, emotion.title())

        counter = "people are" if total_emotion[emotion] > 1 else "person is"
        strings.append(f"{total_emotion[emotion]} {counter} {phrase}")

    return "\n".join(strings)
