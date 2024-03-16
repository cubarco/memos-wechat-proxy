# -*- coding: UTF-8 -*-

from flask import Flask
from flask import request
import hashlib
import xml.etree.ElementTree as ET
import json
import time
import requests
import configparser
import urllib.request
import os
import filetype
from threading import Timer

file = 'config.ini'
con = configparser.ConfigParser()
con.read(file, encoding='utf-8')

app = Flask(__name__)

appid = con.get('prod', 'wechat_appid')
secret = con.get('prod', 'wechat_appsecret')
memos_accesstoken = con.get('prod', 'memos_accesstoken')

access_token = ""


@app.route("/")
def index():
    return "hello, world"


@app.route("/wechat", methods=["GET", "POST"])
def wexin():
    if request.method == "GET":
        my_signature = request.args.get('signature')
        my_timestamp = request.args.get('timestamp')
        my_nonce = request.args.get('nonce')
        my_echostr = request.args.get('echostr')

        token = con.get('prod', 'wechat_token')  # 微信公众号的token
        data = [token, my_timestamp, my_nonce]
        data.sort()
        temp = ''.join(data)
        s = hashlib.sha1()
        s.update(temp.encode("utf-8"))
        mysignature = s.hexdigest()
        if my_signature == mysignature:
            return my_echostr
        else:
            return ""
    else:
        xml = ET.fromstring(request.data)

        global access_token, default_tag_data
        toUser = xml.find('ToUserName').text
        fromUser = xml.find('FromUserName').text
        msgType = xml.find("MsgType").text
        createTime = xml.find("CreateTime")
        if con.get('prod', 'wechat_open_id') == "all":
            pass
        elif str(fromUser) not in con.get('prod', 'wechat_open_id'):
            print("该用户的微信 openid 是【 %s 】，如果你允许该用户访问 memos，要记得写入 config.ini 配置文件才行" % (
                fromUser), flush=True)
            return reply_text(fromUser, toUser, "该用户没有权限")

        memos_response_id = ""
        if msgType == "text":
            content = xml.find('Content').text
            if content == r"【收到不支持的消息类型，暂无法显示】":
                return reply_text(fromUser, toUser, "不支持的类型..\n微信支持发送除gif以外的图片/文字/语音/链接分享卡片/视频")
            memos_response_id = memos_post_api(content)
        elif msgType == "image":
            content1 = xml.find('PicUrl').text
            content2 = xml.find('MediaId').text
            img_name, img_path = wechat_image(content1, content2)
            resource_id, filename = memos_post_file_api(img_name, img_path)
            memos_response_id = memos_post_multipart_api(msgType, resource_id)
        elif msgType == "voice":
            content = xml.find('Recognition').text
            mediaid = xml.find('MediaId').text
            voice_name, voice_path = wechat_voice(mediaid)
            resource_id, filename = memos_post_file_api(voice_name, voice_path)
            memos_response_id = memos_post_multipart_api(msgType, resource_id, content)
        elif msgType == "video":
            thumb_mediaid = xml.find('ThumbMediaId').text
            mediaid = xml.find('MediaId').text
            video_name, video_path = wechat_video(mediaid)
            resource_id, filename = memos_post_file_api(video_name, video_path)
            memos_response_id = memos_post_multipart_api(msgType, resource_id)
        elif msgType == "link":
            link_title = xml.find('Title').text
            link_description = xml.find('Description').text
            link_url = xml.find('Url').text
            content = "%s\n%s\n%s\n%s" % (
                link_title, link_description, link_url, default_tag_data)
            memos_response_id = memos_post_api(content)
        else:
            return reply_text(fromUser, toUser, "不支持的类型..微信只支持发送除gif以外的图片/文字/语音/链接分享卡片")

        if len(str(memos_response_id)) != "":
            return reply_text(fromUser, toUser, "%s") % (con.get('prod', 'messages_success'))
        else:
            return reply_text(fromUser, toUser, "%s").format(con.get('prod', 'messages_failed'))


def memos_post_api(content):
    """
    这个函数是把微信公众号用户的提交信息推送到memos，然后返回提交id。
    """
    global default_tag_data, memos_accesstoken
    url = con.get('prod', 'memos_url') + "/api/v1/memo"

    payload = json.dumps({
        "content": "%s\n%s" % (content, default_tag_data)
    })
    headers = {
        'Authorization': f'Bearer {memos_accesstoken}',
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    r1 = json.loads(response.text)
    return r1["data"]["id"]


def reply_text(to_user, from_user, content):
    """
    以文本类型的方式回复请求
    """
    return """
    <xml>
        <ToUserName><![CDATA[{}]]></ToUserName>
        <FromUserName><![CDATA[{}]]></FromUserName>
        <CreateTime>{}</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[{}]]></Content>
    </xml>
    """.format(to_user, from_user, int(time.time() * 1000), content)


def wechat_image(picurl, mediaId):
    if not os.path.exists("./resource"):
        os.makedirs("./resource")

    img_path0 = "./resource/%s" % (mediaId)
    img_name = ""

    i_response = urllib.request.urlopen(picurl)
    img = i_response.read()

    with open(img_path0, 'wb') as f:
        f.write(img)
    img_type = filetype.guess(img_path0)
    if img_type is None:
        img_name = "%s.jpg" % (mediaId)
        img_path = "%s.jpg" % (img_path0)
        img_mime = "image/jpeg"
    else:
        img_name = "%s.%s" % (mediaId, img_type.extension)
        img_path = "%s.%s" % (img_path0, img_type.extension)
        img_mime = img_type.mime
    os.rename(img_path0, img_path)
    return img_name, img_path


def wechat_voice(mediaId):
    global access_token
    if not os.path.exists("./resource"):
        os.makedirs("./resource")

    url = "https://api.weixin.qq.com/cgi-bin/media/get?access_token=%s&media_id=%s" % (
        access_token, mediaId)
    r = requests.get(url)
    voice_path = "./resource/%s.amr" % (mediaId)
    voice_name = "%s.amr" % (mediaId)

    with open(voice_path, 'wb') as f:
        f.write(r.content)
    voice_type = filetype.guess(voice_path)
    return voice_name, voice_path


def wechat_video(mediaId):
    global access_token
    if not os.path.exists("./resource"):
        os.makedirs("./resource")

    url = "https://api.weixin.qq.com/cgi-bin/media/get?access_token=%s&media_id=%s" % (
        access_token, mediaId)
    r = requests.get(url)
    video_path = "./resource/%s.mp4" % (mediaId)
    video_name = "%s.mp4" % (mediaId)

    with open(video_path, 'wb') as f:
        f.write(r.content)
    video_type = filetype.guess(video_path)
    return video_name, video_path


def memos_post_file_api(file_name, file_path):
    global memos_accesstoken
    url = con.get('prod', 'memos_url') + "/api/v1/resource/blob"
    payload = {}
    file_type = filetype.guess(file_path)
    if file_type is None:
        file_mime = "image/jpeg"
    else:
        file_mime = file_type.mime
    files = [
        ('file', (file_name, open(file_path, 'rb'), file_mime))
    ]
    headers = {
        'Authorization': f'Bearer {memos_accesstoken}',
    }

    response = requests.request(
        "POST", url, headers=headers, data=payload, files=files)

    del_local_file(file_path)
    res_json = json.loads(response.text)
    return res_json["data"]["id"], res_json["data"]["filename"]


def memos_post_multipart_api(msgType, resource_id, content=""):
    global default_tag_data, memos_accesstoken
    resource_list = []
    resource_list.append(resource_id)
    if msgType == "voice":
        data = {"content": "%s\n%s" % (
            content, default_tag_data), "visibility": "PRIVATE", "resourceIdList": resource_list}
    else:
        data = {"content": default_tag_data,
                "visibility": "PRIVATE", "resourceIdList": resource_list}
    url = con.get('prod', 'memos_url') + "/api/v1/memo"
    headers = {
        'Authorization': f'Bearer {memos_accesstoken}',
    }
    response = requests.post(url, json=data, headers=headers)
    r = json.loads(response.text)
    memos_response_id = r["data"]["id"]
    return memos_response_id


def memos_create_default_tags():
    global memos_accesstoken
    memos_default_tags = con.get('prod', 'memos_default_tags').split(';')
    default_tag_data = ""
    headers = {
        'Authorization': f'Bearer {memos_accesstoken}',
    }
    for tag in memos_default_tags:
        if tag:
            default_tag_data = default_tag_data + " #%s" % tag
            tags = {"name": tag}
            requests.post(con.get('prod', 'memos_url') + '/api/v1/tag', json=tags, headers=headers)
    default_tag_data = default_tag_data.lstrip()
    return default_tag_data


def del_local_file(file_path):
    files_del = con.get('prod', 'files_del')
    if files_del == "yes":
        os.remove(file_path)
    else:
        pass


def get_access_token(appid, secret, grant_type="client_credential"):
    url = "https://api.weixin.qq.com/cgi-bin/token?grant_type=%s&appid=%s&secret=%s" % (
        grant_type, appid, secret)
    r = requests.get(url)
    print(r.json(), flush=True)
    return r.json()["access_token"], r.json()["expires_in"]


def auto_refresh_access_token():
    global timer, appid, secret, access_token
    access_token, expires_in = get_access_token(appid, secret)
    timer = Timer((expires_in-150), auto_refresh_access_token)
    timer.start()


if __name__ == "__main__":
    host = con.get('prod', 'flask_host')
    port = con.get('prod', 'flask_port')

    auto_refresh_access_token()
    default_tag_data = memos_create_default_tags()

    app.run(host=host, port=port)
