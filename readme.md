<h1 align="center">Long-Novel-GPT</h1>

<p align="center">
  AI一键生成长篇小说
</p>

<p align="center">
  <a href="#关于项目">关于项目</a> •
  <a href="#更新日志">更新日志</a> •
  <a href="#小说生成prompt">小说生成Prompt</a> •
  <a href="#快速上手">快速上手</a> •
  <a href="#demo使用指南">Demo使用指南</a> •
  <a href="#贡献">贡献</a>
</p>

<hr>

<h2 id="关于项目">🎯 关于项目</h2>

该项目包括一个基于 GPT 等大语言模型的长篇小说生成器，同时还有各类小说生成 Prompt 以及教程。我们欢迎社区贡献，持续更新以提供最佳的小说创作体验。

### 💡 设计思路
Long-Novel-GPT是一个基于GPT等大语言模型的长篇小说生成器。它采用层次化的大纲/章节/正文结构，以把握长篇小说的连贯剧情；通过大纲->章节->正文的精准映射来获取上下文，从而优化API调用成本；并根据自身或用户反馈不断进行优化，直至创作出你心目中的长篇小说。

### 🌟 关键特性

- **结构化写作**：层次化结构有效把握长篇小说的发展脉络
- **反思循环**：持续优化生成的大纲、章节和正文内容
- **成本优化**：智能上下文管理，确保 API 调用费用固定
- **社区驱动**：欢迎贡献 Prompt 和改进建议，共同推动项目发展

<h2 id="更新日志">📅 更新日志</h2>

### 🎉 Long-Novel-GPT 2.0.0 更新（12月4日最新）
- 在线演示：[Long-Novel-GPT Demo](http://14.103.180.212/)
- 提供全新的UI界面

### 🎉 Long-Novel-GPT 1.10 更新（11月28日）
- 在创作时支持单独对选中的段落进行重新创作（通过引用文本）
- 大纲、章节、正文的生成Prompt得到了优化


### 🎉 Long-Novel-GPT 1.9 更新（11月16日）
- 对于大纲、章节、正文分别内置了三种Prompt可供选择：新建、扩写、润色
- 支持输入自己的Prompt
- Prompt预览的交互逻辑更好了
- 支持一键生成，将自动帮你进行全部大纲、章节、正文的生成
- 新增支持智谱GLM模型


### 🎉 Long-Novel-GPT 1.8 更新（11月1日）
- 新增支持多种大语言模型：
  - OpenAI系列: o1-preivew、o1-mini、gpt4o 等
  - Claude系列: Claude-3.5-Sonnet 等
  - 文心一言: ERNIE-4.0、ERNIE-3.5、ERNIE-Novel
  - 豆包: doubao-lite/pro系列
  - 支持任何兼容OpenAI接口的自定义模型
- 优化了生成界面和用户体验

### 🎉 Long-Novel-GPT 1.7 更新（10月29日）

- 提供了一个在线Demo，支持从一句话创意直接生成全书。


### 🔮 后续更新计划
- 考虑一个更美观更实用的编辑界面（已完成）
- 支持文心 Novel 模型（已完成）
- 支持豆包模型（已完成）
- 通过一个创意直接一键生成完整长篇小说（进行中）
- 支持生成大纲和章节（进行中）


### 📜 之前版本
Long-Novel-GPT 1.5及之前版本提供了一个完整的长篇小说生成APP，但是在操作体验上并不完善。从1.6版本起，将更加注重用户体验，重写了一个新的界面，并将项目文件搬到了[core](core)目录下。之前的[demo](demo/app.py)已经不支持了，如果想要体验，可以选择之前的commit进行下载。

<h2 id="小说生成prompt">📚 小说生成 Prompt</h2>

| Prompt | 描述 |
|--------|------|
| [天蚕土豆风格](custom/根据提纲创作正文/天蚕土豆风格.txt) | 用于根据提纲创作正文，模仿天蚕土豆的写作风格 |
| [对草稿进行润色](custom/根据提纲创作正文/对草稿进行润色.txt) | 对你写的网文初稿进行润色和改进 |

[📝 提交你的 Prompt](https://github.com/MaoXiaoYuZ/Long-Novel-GPT/issues/new?assignees=&labels=prompt&template=custom_prompt.md&title=新的Prompt)

<h2 id="快速上手">🚀 快速上手</h2>

### 在线 Demo

无需安装，立即体验我们的在线 Demo：[Long-Novel-GPT Demo](http://14.103.180.212/)

<p align="center">
  <img src="assets/write_text_preview.gif" alt="创作界面预览" width="600"/>
  <br>
  <em>多线程并行创作（<a href="assets/write_text_preview.gif">图中</a>展示的是创作剧情的场景）</em>
</p>


### Docker一键部署

运行下面命令拉取long-novel-gpt镜像
```bash
docker pull maoxiaoyuz/long-novel-gpt:2.0.0
```

下载或复制[.env.example](.env.example)文件，将其放在你的任意一个目录下，将其改名为 **.env**, 并根据文件中提示填写API设置。

填写完成后在该 **.env**文件目录下，运行以下命令：
```bash
docker run -p 80:80 --env-file .env -d maoxiaoyuz/long-novel-gpt:2.0.0
```

接下来访问 http://localhost 即可使用，如果是部署在服务器上，则访问你的服务器公网地址即可。


<p align="center">
  <img src="assets/LNGPT-V2.0.png" alt="Gradio DEMO有5个Tab页面" width="600"/>
</p>

### 使用本地的大模型服务
要使用本地的大模型服务，只需要在Docker部署时额外注意以下两点。

第一，启动Docker的命令需要添加额外参数，具体如下：
```bash
docker run -p 80:80 --env-file .env -d --add-host=host.docker.internal:host-gateway maoxiaoyuz/long-novel-gpt:2.0.0
```

第二，将本地的大模型服务暴露为OpenAI格式接口，在[.env.example](.env.example)文件中进行配置，同时GPT_BASE_URL中localhost或127.0.0.1需要替换为：**host.docker.internal**
例如
```
# 这里GPT_BASE_URL格式只提供参考，主要是替换localhost或127.0.0.1
GPT_BASE_URL=http://host.docker.internal:7777/v1
GPT_API_KEY=you_api_key
GPT_DEFAULT_MODEL=model_name1
GPT_DEFAULT_SUB_MODEL=model_name2
```

<h2 id="demo使用指南">🖥️ Demo 使用指南</h2>

### 当前Demo能生成百万字小说吗？
Long-Novel-GPT-2.0.0版本完全支持生成百万级别小说的版本，而且是多窗口同步生成，速度非常快。

同时你可以自由控制你需要生成的部分，对选中部分重新生成等等。

而且，Long-Novel-GPT-2.0.0会自动管理上下文，在控制API调用费用的同时确保了生成剧情的连续。

在2.0.0版本中，你需要部署在本地并采用自己的API-Key，在[.env.example](.env.example)文件中配置生成时采用的最大线程数。
```
# Thread Configuration - 线程配置
# 生成时采用的最大线程数
MAX_THREAD_NUM=5
```
在线Demo是不行的，因为最大线程为5。

### 如何利用LN-GPT-2.0.0生成百万字小说？
首先，你需要部署在本地，配置API-Key并解除线程限制。

然后，在**创作大纲**阶段，需要生成大概40行的剧情，每行50字，这里就有2000字了。（通过不断点击**扩写全部大纲**）

其次，在**创作剧情**阶段，将大纲2k字扩充到20k字。（10+线程并行）

最后，在**创作正文**阶段，将20K字扩充到100k字。（50+线程并行）


### LN-GPT-2.0.0生成的百万字小说怎么样？
总的来说，2.0.0版本能够实现在用户监督下生成达到签约门槛的网文。

而且，我们的最终目标始终是实现一键生成全书，将在2-3个版本迭代后正式推出。

<h2 id="贡献">🤝 贡献</h2>

我们欢迎所有形式的贡献，无论是新功能的建议、代码改进，还是 bug 报告。请通过 GitHub issues 或 pull requests 与我们联系。

大家也可以加入群，在群里讨论。

<p align="center">
  <img src="assets/group.jpg" alt="企业微信群二维码" width="300"/>
</p>
