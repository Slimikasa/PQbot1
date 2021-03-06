import aiohttp
import base64
import json
from io import BytesIO
import nonebot
from omega_miya.utils.Omega_Base import DBTable, Result

DYNAMIC_API_URL = 'https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history'
GET_DYNAMIC_DETAIL_API_URL = 'https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail'
USER_INFO_API_URL = 'https://api.bilibili.com/x/space/acc/info'
DYNAMIC_URL = 'https://t.bilibili.com/'

global_config = nonebot.get_driver().config
BILI_SESSDATA = global_config.bili_sessdata
BILI_CSRF = global_config.bili_csrf
BILI_UID = global_config.bili_uid


def check_bili_cookies() -> Result:
    cookies = {}
    if BILI_SESSDATA and BILI_CSRF:
        cookies.update({'SESSDATA': BILI_SESSDATA})
        cookies.update({'bili_jct': BILI_CSRF})
        return Result(error=False, info='Success', result=cookies)
    else:
        return Result(error=True, info='None', result=cookies)


async def fetch_json(url: str, paras: dict = None) -> Result:
    cookies = None
    cookies_res = check_bili_cookies()
    if cookies_res.success():
        cookies = cookies_res.result
    timeout_count = 0
    error_info = ''
    while timeout_count < 3:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {'accept': 'application/json, text/plain, */*',
                           'accept-encoding': 'gzip, deflate, br',
                           'accept-language:': 'zh-CN,zh;q=0.9',
                           'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
                           'origin': 'https://t.bilibili.com',
                           'referer': 'https://t.bilibili.com/'}
                async with session.get(url=url, params=paras, headers=headers, cookies=cookies, timeout=timeout) as rp:
                    _json = await rp.json()
                result = Result(error=False, info='Success', result=_json)
            return result
        except Exception as e:
            error_info += f'{repr(e)} Occurred in fetch_json trying {timeout_count + 1} using paras: {paras}\n'
        finally:
            timeout_count += 1
    else:
        error_info += f'Failed too many times in fetch_json using paras: {paras}'
        result = Result(error=True, info=error_info, result={})
        return result


# ?????????base64
async def pic_2_base64(url: str) -> Result:
    async def get_image(pic_url: str):
        timeout_count = 0
        error_info = ''
        while timeout_count < 3:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
                               'origin': 'https://t.bilibili.com',
                               'referer': 'https://t.bilibili.com/'}
                    async with session.get(url=pic_url, headers=headers, timeout=timeout) as resp:
                        _res = await resp.read()
                return _res
            except Exception as _e:
                error_info += f'{repr(_e)} Occurred in pic_2_base64 trying {timeout_count + 1} using paras: {pic_url}\n'
            finally:
                timeout_count += 1
        else:
            error_info += f'Failed too many times in pic_2_base64 using paras: {pic_url}'
            return None

    origin_image_f = BytesIO()
    try:
        origin_image_f.write(await get_image(pic_url=url))
    except Exception as e:
        result = Result(error=True, info=f'pic_2_base64 error: {repr(e)}', result='')
        return result
    b64 = base64.b64encode(origin_image_f.getvalue())
    b64 = str(b64, encoding='utf-8')
    b64 = 'base64://' + b64
    origin_image_f.close()
    result = Result(error=False, info='Success', result=b64)
    return result


# ????????????uid??????????????????
async def get_user_info(user_uid) -> Result:
    url = USER_INFO_API_URL
    payload = {'mid': user_uid}
    result = await fetch_json(url=url, paras=payload)
    if not result.success():
        return result
    else:
        user_info = dict(result.result)
        try:
            _res = {
                'status': user_info['code'],
                'name': user_info['data']['name']
            }
            result = Result(error=False, info='Success', result=_res)
        except Exception as e:
            result = Result(error=True, info=f'User info parse failed: {repr(e)}', result={})
    return result


# ????????????up???????????????id?????????
def get_user_dynamic(user_id: int) -> Result:
    t = DBTable(table_name='Bilidynamic')
    _res = t.list_col_with_condition('dynamic_id', 'uid', user_id)
    if not _res.success():
        return _res
    dynamic_list = []
    for item in _res.result:
        dynamic_list.append(int(item[0]))
    result = Result(error=False, info='Success', result=dynamic_list)
    return result


# ??????????????????????????????????????????
async def get_user_dynamic_history(dy_uid) -> Result:
    _DYNAMIC_INFO = {}  # ??????????????????????????????????????????
    url = DYNAMIC_API_URL
    if BILI_UID:
        payload = {'visitor_uid': BILI_UID, 'host_uid': dy_uid,
                   'offset_dynamic_id': 0, 'need_top': 0, 'platform': 'web'}
    else:
        payload = {'host_uid': dy_uid, 'offset_dynamic_id': 0, 'need_top': 0, 'platform': 'web'}

    result = await fetch_json(url=url, paras=payload)
    if not result.success():
        return result
    else:
        dynamic_info = dict(result.result)
        if not dynamic_info.get('data'):
            result = Result(error=True, info=f"Get dynamic info failed: {dynamic_info.get('message')}", result={})
            return result
    for card_num in range(len(dynamic_info['data']['cards'])):
        cards = dynamic_info['data']['cards'][card_num]
        card = json.loads(cards['card'])
        '''
        ??????type????????????: 
        1 ??????
        2 ??????(?????????)
        4 ??????(?????????)
        8 ????????????
        16 ?????????(???playurl??????)
        32 ????????????
        64 ??????
        256 ??????
        512 ????????????(???????????????)
        1024 ??????(????????????)
        2048 B???????????????(????????????, ???????????????????????)(????????????)
        '''
        # type=1, ???????????????????????????
        if cards['desc']['type'] == 1:
            # ???????????????ID
            dy_id = cards['desc']['dynamic_id']
            # ?????????????????????
            url = DYNAMIC_URL + str(cards['desc']['dynamic_id'])
            # ??????????????????????????????
            name = cards['desc']['user_profile']['info']['uname']
            # ????????????????????????????????????
            content = card['item']['content']
            # ???????????????????????????id
            origin_dynamic_id = cards['desc']['origin']['dynamic_id']
            card_dic = dict({'id': dy_id, 'type': 1, 'url': url,
                             'name': name, 'content': content, 'origin': origin_dynamic_id})
            _DYNAMIC_INFO[card_num] = card_dic
        # type=2, ???????????????????????????(?????????)
        elif cards['desc']['type'] == 2:
            # ???????????????ID
            dy_id = cards['desc']['dynamic_id']
            # ?????????????????????
            url = DYNAMIC_URL + str(cards['desc']['dynamic_id'])
            # ??????????????????????????????
            name = cards['desc']['user_profile']['info']['uname']
            # ?????????????????????
            description = card['item']['description']
            # ????????????????????????
            pic_urls = []
            for pic_info in card['item']['pictures']:
                pic_urls.append(pic_info['img_src'])
            card_dic = dict({'id': dy_id, 'type': 2, 'url': url, 'pic_urls': pic_urls,
                             'name': name, 'content': description, 'origin': ''})
            _DYNAMIC_INFO[card_num] = card_dic
        # type=4, ???????????????????????????(?????????)
        elif cards['desc']['type'] == 4:
            # ???????????????ID
            dy_id = cards['desc']['dynamic_id']
            # ?????????????????????
            url = DYNAMIC_URL + str(cards['desc']['dynamic_id'])
            # ??????????????????????????????
            name = cards['desc']['user_profile']['info']['uname']
            # ?????????????????????
            description = card['item']['content']
            card_dic = dict({'id': dy_id, 'type': 4, 'url': url,
                             'name': name, 'content': description, 'origin': ''})
            _DYNAMIC_INFO[card_num] = card_dic
        # type=8, ??????????????????
        elif cards['desc']['type'] == 8:
            # ???????????????ID
            dy_id = cards['desc']['dynamic_id']
            # ?????????????????????
            url = DYNAMIC_URL + str(cards['desc']['dynamic_id'])
            # ??????????????????????????????
            name = cards['desc']['user_profile']['info']['uname']
            # ??????????????????????????????
            content = card['dynamic']
            title = card['title']
            card_dic = dict({'id': dy_id, 'type': 8, 'url': url,
                             'name': name, 'content': content, 'origin': title})
            _DYNAMIC_INFO[card_num] = card_dic
        # type=16, ???????????????(???????????????????????????)
        elif cards['desc']['type'] == 16:
            # ???????????????ID
            dy_id = cards['desc']['dynamic_id']
            # ?????????????????????
            url = DYNAMIC_URL + str(cards['desc']['dynamic_id'])
            # ??????????????????????????????
            name = cards['desc']['user_profile']['info']['uname']
            # ????????????
            try:
                content = card['item']['description']
            except (KeyError, TypeError):
                content = card['item']['desc']
            card_dic = dict({'id': dy_id, 'type': 16, 'url': url,
                             'name': name, 'content': content, 'origin': ''})
            _DYNAMIC_INFO[card_num] = card_dic
        # type=32, ??????????????????
        elif cards['desc']['type'] == 32:
            # ???????????????ID
            dy_id = cards['desc']['dynamic_id']
            # ?????????????????????
            url = DYNAMIC_URL + str(cards['desc']['dynamic_id'])
            # ??????????????????????????????
            name = cards['desc']['user_profile']['info']['uname']
            # ??????????????????
            title = card['title']
            card_dic = dict({'id': dy_id, 'type': 32, 'url': url,
                             'name': name, 'content': '', 'origin': title})
            _DYNAMIC_INFO[card_num] = card_dic
        # type=64, ??????????????????
        elif cards['desc']['type'] == 64:
            # ???????????????ID
            dy_id = cards['desc']['dynamic_id']
            # ?????????????????????
            url = DYNAMIC_URL + str(cards['desc']['dynamic_id'])
            # ??????????????????????????????
            name = cards['desc']['user_profile']['info']['uname']
            # ??????????????????????????????
            content = card['summary']
            title = card['title']
            card_dic = dict({'id': dy_id, 'type': 64, 'url': url,
                             'name': name, 'content': content, 'origin': title})
            _DYNAMIC_INFO[card_num] = card_dic
        # type=256, ????????????
        elif cards['desc']['type'] == 256:
            # ???????????????ID
            dy_id = cards['desc']['dynamic_id']
            # ?????????????????????
            url = DYNAMIC_URL + str(cards['desc']['dynamic_id'])
            # ??????????????????????????????
            name = cards['desc']['user_profile']['info']['uname']
            # ?????????????????????
            description = card['intro']
            title = card['title']
            card_dic = dict({'id': dy_id, 'type': 256, 'url': url,
                             'name': name, 'content': description, 'origin': title})
            _DYNAMIC_INFO[card_num] = card_dic
        # type=512, ????????????????????????
        elif cards['desc']['type'] == 512:
            # ???????????????ID
            dy_id = cards['desc']['dynamic_id']
            # ?????????????????????
            url = DYNAMIC_URL + str(cards['desc']['dynamic_id'])
            # ??????????????????????????????
            name = cards['desc']['user_profile']['info']['uname']
            # ??????????????????
            title = card['apiSeasonInfo']['title']
            card_dic = dict({'id': dy_id, 'type': 512, 'url': url,
                             'name': name, 'content': '', 'origin': title})
            _DYNAMIC_INFO[card_num] = card_dic
        # type=2048, B???????????????
        elif cards['desc']['type'] == 2048:
            # ???????????????ID
            dy_id = cards['desc']['dynamic_id']
            # ?????????????????????
            url = DYNAMIC_URL + str(cards['desc']['dynamic_id'])
            # ??????????????????????????????
            name = cards['desc']['user_profile']['info']['uname']
            # ?????????????????????
            content = card['vest']['content']
            # ???????????????????????????
            origin = str(card['sketch']['title']) + ' - ' + str(card['sketch']['desc_text'])
            card_dic = dict({'id': dy_id, 'type': 2048, 'url': url,
                             'name': name, 'content': content, 'origin': origin})
            _DYNAMIC_INFO[card_num] = card_dic
        else:
            # ??????????????????
            dy_id = cards['desc']['dynamic_id']
            # ?????????????????????
            url = DYNAMIC_URL + str(cards['desc']['dynamic_id'])
            name = 'Unknown'
            card_dic = dict({'id': dy_id, 'type': -1, 'url': url,
                             'name': name, 'content': '', 'origin': ''})
            _DYNAMIC_INFO[card_num] = card_dic
    return Result(error=False, info='Success', result=_DYNAMIC_INFO)


async def get_dynamic_info(dynamic_id) -> Result:
    __payload = {'dynamic_id': dynamic_id}
    _res = await fetch_json(url=GET_DYNAMIC_DETAIL_API_URL, paras=__payload)
    if not _res.success():
        return _res
    else:
        try:
            origin_dynamic = dict(_res.result)
            origin_card = origin_dynamic['data']['card']
            origin_name = origin_card['desc']['user_profile']['info']['uname']
            origin_pics_list = []
            if origin_card['desc']['type'] == 1:
                origin_description = json.loads(origin_card['card'])['item']['content']
            elif origin_card['desc']['type'] == 2:
                origin_description = json.loads(origin_card['card'])['item']['description']
                origin_pics = json.loads(origin_card['card'])['item']['pictures']
                for item in origin_pics:
                    try:
                        origin_pics_list.append(item['img_src'])
                    except (KeyError, TypeError):
                        continue
            elif origin_card['desc']['type'] == 4:
                origin_description = json.loads(origin_card['card'])['item']['content']
            elif origin_card['desc']['type'] == 8:
                origin_description = json.loads(origin_card['card'])['dynamic']
                if not origin_description:
                    origin_description = json.loads(origin_card['card'])['title']
            elif origin_card['desc']['type'] == 16:
                origin_description = json.loads(origin_card['card'])['item']['description']
            elif origin_card['desc']['type'] == 32:
                origin_description = json.loads(origin_card['card'])['title']
            elif origin_card['desc']['type'] == 64:
                origin_description = json.loads(origin_card['card'])['summary']
            elif origin_card['desc']['type'] == 256:
                origin_description = json.loads(origin_card['card'])['intro']
            elif origin_card['desc']['type'] == 512:
                origin_description = json.loads(origin_card['card'])['apiSeasonInfo']['title']
            elif origin_card['desc']['type'] == 2048:
                origin_description = json.loads(origin_card['card'])['vest']['content']
            else:
                origin_description = ''
            origin = dict({'id': dynamic_id, 'type': origin_card['desc']['type'], 'url': '',
                           'name': origin_name, 'content': origin_description, 'origin': '',
                           'origin_pics': origin_pics_list})
            result = Result(error=False, info='Success', result=origin)
        except Exception as e:
            # ??????????????????
            origin = dict({'id': dynamic_id, 'type': -1, 'url': '',
                           'name': 'Unknown', 'content': '??????????????????', 'origin': repr(e)})
            result = Result(error=True, info='Dynamic not found', result=origin)
        return result


__all__ = [
    'pic_2_base64',
    'get_user_info',
    'get_user_dynamic',
    'get_user_dynamic_history',
    'get_dynamic_info'
]

if __name__ == '__main__':
    import asyncio

    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(get_user_dynamic_history(dy_uid=846180))
    print(res)
