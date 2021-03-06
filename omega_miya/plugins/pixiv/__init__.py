import re
from nonebot import on_command, export, logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import GroupMessageEvent
from nonebot.adapters.cqhttp.permission import GROUP
from nonebot.adapters.cqhttp import MessageSegment, Message
from omega_miya.utils.Omega_plugin_utils import init_export
from omega_miya.utils.Omega_plugin_utils import has_command_permission, has_level_or_node
from .utils import fetch_json, fetch_image, API_KEY, RANK_API_URL

# Custom plugin usage text
__plugin_raw_name__ = __name__.split('.')[-1]
__plugin_name__ = 'Pixiv'
__plugin_usage__ = r'''【Pixiv助手】
查看Pixiv插画, 以及随机日榜、周榜、月榜

**Permission**
Command & Lv.50
or AuthNode

**AuthNode**
basic

**Usage**
/pixiv [PID]
/pixiv 日榜
/pixiv 周榜
/pixiv 月榜'''

# 声明本插件可配置的权限节点
__plugin_auth_node__ = [
    'basic'
]

# Init plugin export
init_export(export(), __plugin_name__, __plugin_usage__, __plugin_auth_node__)


# 注册事件响应器
pixiv = on_command('pixiv', rule=has_command_permission() & has_level_or_node(50, __plugin_raw_name__, 'basic'),
                   aliases={'Pixiv'}, permission=GROUP, priority=20, block=True)


# 修改默认参数处理
@pixiv.args_parser
async def parse(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        await pixiv.reject('你似乎没有发送有效的参数呢QAQ, 请重新发送:')
    state[state["_current_key"]] = args[0]
    if state[state["_current_key"]] == '取消':
        await pixiv.finish('操作已取消')


@pixiv.handle()
async def handle_first_receive(bot: Bot, event: GroupMessageEvent, state: T_State):
    args = str(event.get_plaintext()).strip().lower().split()
    if not args:
        pass
    elif args and len(args) == 1:
        state['mode'] = args[0]
    else:
        await pixiv.finish('参数错误QAQ')


@pixiv.got('mode', prompt='你是想看日榜, 周榜, 月榜, 还是作品呢? 想看特定作品的话请输入PixivID~')
async def handle_pixiv(bot: Bot, event: GroupMessageEvent, state: T_State):
    mode = state['mode']
    if mode == '日榜':
        await pixiv.send('稍等, 正在下载资源~')
        payload = {'key': API_KEY, 'num': 3, 'mode': 'daily'}
        _res = await fetch_json(url=RANK_API_URL, paras=payload)
        rank_data = _res.result
        if _res.success() and not rank_data.get('error'):
            error_count = 0
            for pid in rank_data.get('body'):
                logger.debug(f'获取Pixiv资源: {pid}.')
                # 获取illust
                _res = await fetch_image(pid=pid)
                if _res.success():
                    msg = _res.result.get('msg')
                    img_seg = MessageSegment.image(_res.result.get('b64'))
                    # 发送图片和图片信息
                    await pixiv.send(Message(img_seg).append(msg))
                else:
                    logger.warning(f"User: {event.user_id} 获取Pixiv资源失败, 网络超时或 {pid} 不存在")
                    error_count += 1
            else:
                if error_count == len(rank_data.get('body')):
                    await pixiv.finish('加载失败, 网络超时QAQ')
        else:
            logger.warning(f"User: {event.user_id} 获取Pixiv Rank失败, 网络超时")
            await pixiv.finish('加载失败, 网络超时QAQ')
    elif mode == '周榜':
        await pixiv.send('稍等, 正在下载资源~')
        payload = {'key': API_KEY, 'num': 3, 'mode': 'weekly'}
        _res = await fetch_json(url=RANK_API_URL, paras=payload)
        rank_data = _res.result
        if _res.success() and not rank_data.get('error'):
            error_count = 0
            for pid in rank_data.get('body'):
                logger.debug(f'获取Pixiv资源: {pid}.')
                # 获取illust
                _res = await fetch_image(pid=pid)
                if _res.success():
                    msg = _res.result.get('msg')
                    img_seg = MessageSegment.image(_res.result.get('b64'))
                    # 发送图片和图片信息
                    await pixiv.send(Message(img_seg).append(msg))
                else:
                    logger.warning(f"User: {event.user_id} 获取Pixiv资源失败, 网络超时或 {pid} 不存在")
                    error_count += 1
            else:
                if error_count == len(rank_data.get('body')):
                    await pixiv.finish('加载失败, 网络超时QAQ')
        else:
            logger.warning(f"User: {event.user_id} 获取Pixiv Rank失败, 网络超时")
            await pixiv.finish('加载失败, 网络超时QAQ')
    elif mode == '月榜':
        await pixiv.send('稍等, 正在下载资源~')
        payload = {'key': API_KEY, 'num': 3, 'mode': 'monthly'}
        _res = await fetch_json(url=RANK_API_URL, paras=payload)
        rank_data = _res.result
        if _res.success() and not rank_data.get('error'):
            error_count = 0
            for pid in rank_data.get('body'):
                logger.debug(f'获取Pixiv资源: {pid}.')
                # 获取illust
                _res = await fetch_image(pid=pid)
                if _res.success():
                    msg = _res.result.get('msg')
                    img_seg = MessageSegment.image(_res.result.get('b64'))
                    # 发送图片和图片信息
                    await pixiv.send(Message(img_seg).append(msg))
                else:
                    logger.warning(f"User: {event.user_id} 获取Pixiv资源失败, 网络超时或 {pid} 不存在")
                    error_count += 1
            else:
                if error_count == len(rank_data.get('body')):
                    await pixiv.finish('加载失败, 网络超时QAQ')
        else:
            logger.warning(f"User: {event.user_id} 获取Pixiv Rank失败, 网络超时")
            await pixiv.send('加载失败, 网络超时QAQ')
    elif re.match(r'^\d+$', mode):
        pid = mode
        logger.debug(f'获取Pixiv资源: {pid}.')
        await pixiv.send('稍等, 正在下载图片~')
        # 获取illust
        _res = await fetch_image(pid=pid)
        if _res.success():
            msg = _res.result.get('msg')
            img_seg = MessageSegment.image(_res.result.get('b64'))
            # 发送图片和图片信息
            await pixiv.send(Message(img_seg).append(msg))
        else:
            logger.warning(f"User: {event.user_id} 获取Pixiv资源失败, 网络超时或 {pid} 不存在")
            await pixiv.send('加载失败, 网络超时或没有这张图QAQ')
    else:
        await pixiv.reject('你输入的命令好像不对呢……请输入"月榜"、"周榜"、"日榜"或者PixivID, 取消命令请发送【取消】:')
