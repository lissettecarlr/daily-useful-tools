# 番剧重命名工具

## 设计流程

1. 输入番剧文件夹
2. 遍历文件夹中所以视频和字幕文件表
3. 将文件名输入AI生成修改后的文件名
4. 用户检阅后确认修改
5. 重命名


## 使用方法

### 安装环境
```bash
pip install -r requirements.txt
```

### 设置openai
创建.env文件，填入key和url
```bash
OPENAI_API_KEY=sk-T
OPENAI_BASE_URL=https://oneapi.com/v1
```

### 命令行执行

```bash
python src.py [番剧目录路径]
```


## 运行示例
```bash
python src.py ./ex

找到 2 个视频文件和 2 个字幕文件

重命名计划:

视频文件:
./ex\[ANi] 轉生成貓咪的大叔 - 27 [1080P][Baha][WEB-DL][AAC AVC][CHT].mp4
-> ./ex\轉生成貓咪的大叔 - S01E27 - 1080P.WEB-DL.mp4

视频文件:
./ex\[Prejudice-Studio] 終末起點（僅限港澳台地區） - 01 [WEBDL 1080P AVC 8bit AAC MP4][繁体内挂].mp4
-> ./ex\終末起點 - S01E01 - 1080P.WEBDL.mp4

字幕文件:
./ex\終末起點1.ass
-> ./ex\終末起點 - S01E01.ass

字幕文件:
./ex\轉生成貓咪的大叔27.ass
-> ./ex\轉生成貓咪的大叔 - S01E27.ass

是否确认执行重命名？(y/n): y
重命名成功: ./ex\[ANi] 轉生成貓咪的大叔 - 27 [1080P][Baha][WEB-DL][AAC AVC][CHT].mp4 -> ./ex\轉生成貓咪的大叔 - S01E27 - 1080P.WEB-DL.mp4
重命名成功: ./ex\[Prejudice-Studio] 終末起點（僅限港澳台地區） - 01 [WEBDL 1080P AVC 8bit AAC MP4][繁体内挂].mp4 -> ./ex\終末起點 - S01E01 - 1080P.WEBDL.mp4
重命名成功: ./ex\終末起點1.ass -> ./ex\終末起點 - S01E01.ass
重命名成功: ./ex\轉生成貓咪的大叔27.ass -> ./ex\轉生成貓咪的大叔 - S01E27.ass
```




