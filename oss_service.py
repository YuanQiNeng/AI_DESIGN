import oss2
import io
from urllib.parse import urljoin # 用于拼接 URL
from dotenv import  load_dotenv
load_dotenv()
import os
from loguru import logger

# --- 你的配置信息 ---
# 请替换为你自己的阿里云 OSS 信息
ACCESS_KEY_ID = os.getenv("ACCESS_KEY_ID")
ACCESS_KEY_SECRET = os.getenv("ACCESS_KEY_SECRET")
BUCKET_NAME = os.getenv("BUCKET_NAME")
ENDPOINT = 'https://oss-cn-hangzhou.aliyuncs.com' # 你的 Bucket 所在的地域对应的 Endpoint
# 注意：Endpoint 通常是 https://oss-<region>.aliyuncs.com
# 例如，北京是 oss-cn-beijing.aliyuncs.com
# 请根据你的 Bucket 实际所在地域选择正确的 Endpoint

def upload_image_bytes_to_oss(image_bytes, object_name, bucket_name=BUCKET_NAME, endpoint=ENDPOINT):
    """
    上传图片的二进制内容到阿里云OSS，并返回访问URL。

    Args:
        image_bytes (bytes): 图片的二进制内容 (例如, requests.get(url).content 或 open(file, 'rb').read())
        object_name (str): 上传到OSS后保存的文件名 (例如 'images/my_picture.jpg')
        bucket_name (str): Bucket 名称
        endpoint (str): Bucket 所在的地域Endpoint

    Returns:
        str: 上传成功后，返回图片的访问URL；失败则返回 None。
    """
    try:
        # 1. 创建认证对象
        auth = oss2.Auth(ACCESS_KEY_ID, ACCESS_KEY_SECRET)

        # 2. 创建Bucket对象
        bucket = oss2.Bucket(auth, endpoint, bucket_name)

        # 3. 准备 headers，设置对象 ACL 为公共读
        headers = {
            'x-oss-object-acl': oss2.OBJECT_ACL_PUBLIC_READ # 设置对象为公共读
        }

        # 4. 上传二进制数据，同时设置 headers
        # image_bytes 是 bytes 类型，可以是 requests.get(url).content 或者 open(file, 'rb').read()
        # object_name 是你希望在OSS上保存的文件路径和名称
        result = bucket.put_object(object_name, image_bytes, headers=headers)

        # 检查上传是否成功
        if result.status == 200:
            # 构造访问URL
            # URL 格式通常为: https://<bucket-name>.<endpoint>/<object-name>
            # 例如: https://my-bucket.oss-cn-hangzhou.aliyuncs.com/images/my_picture.jpg
            image_url = f"https://{bucket_name}.{ENDPOINT.lstrip('https://')}/{object_name}"
            # 或者使用 urljoin
            # image_url = urljoin(f"https://{bucket_name}.{ENDPOINT.lstrip('https://')}", object_name.lstrip('/'))
            logger.info(f"图片上传成功！访问URL: {image_url}")
            return image_url
        else:
            logger.error(f"上传失败，状态码: {result.status}")
            return None

    except oss2.exceptions.OssError as e:
        logger.error(f"OSS 服务错误: {e}")
        return None
    except Exception as e:
        logger.error(f"上传过程中发生未知错误: {e}")
        return None