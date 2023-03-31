
功能：微信公众号推送消息到 [memos](https://github.com/usememos/memos)的代理服务。

原repo文档：[memos备忘录加入微信公众号功能](https://zhaouncle.com/memos%E5%A4%87%E5%BF%98%E5%BD%95%E5%8A%A0%E5%85%A5%E5%BE%AE%E4%BF%A1%E5%85%AC%E4%BC%97%E5%8F%B7%E5%8A%9F%E8%83%BD/)


# 启动


## 1. docker
```bash
docker run -d -p 5000:5000  -v "~/memos-wechat-proxy/config.ini:/app/config.ini" --name memos-wechat-proxy lclrc/memos-wechat-proxy
```

## 2. docker-compose


## 设置
1. 在`~/memos-wechat-proxy`中创建`config.ini`, 并把`config_demo.ini`中全部内容复制进去
2. 根据Memos和公众号修改`config.ini`中的设置(可以适当参考原repo文档)
3. 重启容器


# 构建

```
docker build -t memos-wechat-proxy .
docker tag memos-wechat-proxy lclrc/memos-wechat-proxy
docker push lclrc/memos-wechat-proxy
```
# TODO

- [x] 修复图片
- [x] 支持语音
- [x] 支持视频
- [x] 支持自定义默认标签
