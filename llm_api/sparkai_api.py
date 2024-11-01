from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage as SparkMessage

#星火认知大模型Spark Max的URL值，其他版本大模型URL值请前往文档（https://www.xfyun.cn/doc/spark/Web.html）查看
SPARKAI_URL = 'wss://spark-api.xf-yun.com/v4.0/chat'
#星火认知大模型调用秘钥信息，请前往讯飞开放平台控制台（https://console.xfyun.cn/services/bm35）查看
SPARKAI_APP_ID = '01793781'
SPARKAI_API_SECRET = 'YzJkNTI5N2Q5NDY4N2RlNWI5YjA5ZDM4'
SPARKAI_API_KEY = '5dd33ea830aff0c9dff18e2561a5e6c7'
#星火认知大模型Spark Max的domain值，其他版本大模型domain值请前往文档（https://www.xfyun.cn/doc/spark/Web.html）查看
SPARKAI_DOMAIN = '4.0Ultra'

"""
5dd33ea830aff0c9dff18e2561a5e6c7&YzJkNTI5N2Q5NDY4N2RlNWI5YjA5ZDM4&01793781

domain值:
lite指向Lite版本;
generalv3指向Pro版本;
pro-128k指向Pro-128K版本;
generalv3.5指向Max版本;
max-32k指向Max-32K版本;
4.0Ultra指向4.0 Ultra版本;


Spark4.0 Ultra 请求地址，对应的domain参数为4.0Ultra：
wss://spark-api.xf-yun.com/v4.0/chat
Spark Max-32K请求地址，对应的domain参数为max-32k
wss://spark-api.xf-yun.com/chat/max-32k
Spark Max请求地址，对应的domain参数为generalv3.5
wss://spark-api.xf-yun.com/v3.5/chat
Spark Pro-128K请求地址，对应的domain参数为pro-128k：
wss://spark-api.xf-yun.com/chat/pro-128k
Spark Pro请求地址，对应的domain参数为generalv3：
wss://spark-api.xf-yun.com/v3.1/chat
Spark Lite请求地址，对应的domain参数为lite：
wss://spark-api.xf-yun.com/v1.1/chat
"""


sparkai_model_config = {
    "spark-4.0-ultra": {
        "Pricing": (0, 0),
        "currency_symbol": '￥',
        "url": "wss://spark-api.xf-yun.com/v4.0/chat",
        "domain": "4.0Ultra"
    }
}



if __name__ == '__main__':
    spark = ChatSparkLLM(
        spark_api_url=SPARKAI_URL,
        spark_app_id=SPARKAI_APP_ID,
        spark_api_key=SPARKAI_API_KEY,
        spark_api_secret=SPARKAI_API_SECRET,
        spark_llm_domain=SPARKAI_DOMAIN,
        streaming=True,
    )
    messages = [SparkMessage(
        role="user",
        content='你好呀'
    )]
    a = spark.stream(messages)
    for message in a:
        print(message)  