import json
import os
import re
import sys

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkdns.v2 import (
    DnsClient,
    ShowRecordSetRequest,
    UpdateRecordSetRequest,
    UpdateRecordSetReq,
)
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion

IPV4_RE = re.compile(r"^([0-9]{1,3}\.){3}[0-9]{1,3}$")


def build_client(ak, sk, project_id, region_id):
    credentials = (
        BasicCredentials(ak, sk, project_id) if project_id else BasicCredentials(ak, sk)
    )
    return (
        DnsClient.new_builder()
        .with_credentials(credentials)
        .with_region(DnsRegion.value_of(region_id))
        .build()
    )


def load_records():
    """读取待更新的记录配置。

    优先级说明（重要）：
        只要 DNS_RECORDS 非空，就只使用它，ZONE_ID / RECORD_ID / DOMAIN_NAME 会被忽略。
        这是历史设计，容易造成「明明配了单记录 Secrets 却更新了别的域名」的误解，
        因此这里会显式打印当前模式与冲突提示。
    """
    raw = (os.getenv("DNS_RECORDS") or "").strip()
    single = {
        "zone_id": (os.getenv("ZONE_ID") or "").strip(),
        "record_id": (os.getenv("RECORD_ID") or "").strip(),
        "domain_name": (os.getenv("DOMAIN_NAME") or "").strip(),
    }
    single_ready = all(single.values())

    if raw:
        try:
            data = json.loads(raw)
        except Exception as e:
            print(f"[FATAL] DNS_RECORDS 不是合法 JSON：{e}")
            sys.exit(1)
        if not isinstance(data, list) or not data:
            print("[FATAL] DNS_RECORDS 必须是非空 JSON 数组")
            sys.exit(1)
        print(f"[i] 模式：多记录（DNS_RECORDS），共 {len(data)} 条")
        if single_ready:
            print(
                "[!] 注意：ZONE_ID / RECORD_ID / DOMAIN_NAME 也已配置，"
                "但多记录模式优先级更高，这 3 个值本次不会生效。"
            )
        return data

    if single_ready:
        print("[i] 模式：单记录（ZONE_ID / RECORD_ID / DOMAIN_NAME）")
        return [single]

    print(
        "[FATAL] 未发现有效配置：请提供 DNS_RECORDS，"
        "或同时提供 ZONE_ID / RECORD_ID / DOMAIN_NAME"
    )
    sys.exit(1)


def dedupe(records):
    """去掉重复条目，避免同一条记录在一次运行中被重复更新。"""
    seen, result = set(), []
    for rec in records:
        key = (
            (rec.get("zone_id") or "").strip(),
            (rec.get("record_id") or "").strip(),
        )
        if key in seen:
            print(f"[!] 跳过重复条目：{rec.get('domain_name') or key[1]}")
            continue
        seen.add(key)
        result.append(rec)
    return result


def update_one(client, rec, new_ip):
    zone_id = (rec.get("zone_id") or "").strip()
    record_id = (rec.get("record_id") or "").strip()
    domain = (rec.get("domain_name") or "").strip()

    if not zone_id or not record_id:
        print(f"[FAIL] {domain or '(未命名)'}：zone_id 或 record_id 缺失")
        return False

    # 先查询确认记录存在：把笼统的「更新失败」细化为「ID 已失效」
    try:
        show_req = ShowRecordSetRequest()
        show_req.zone_id = zone_id
        show_req.recordset_id = record_id
        current = client.show_record_set(show_req)
    except exceptions.ClientRequestException as e:
        if e.status_code == 404:
            print(
                f"[FAIL] {domain}：记录不存在（404）。"
                "ZONE_ID / RECORD_ID 已失效或记录已被删除，请重新获取 ID"
            )
        elif e.status_code == 401:
            print(f"[FAIL] {domain}：认证失败（401），请检查 AK/SK 与 HUAWEI_REGION")
        elif e.status_code == 403:
            print(f"[FAIL] {domain}：无权限（403），请为该 AK 对应的 IAM 用户授予 DNS FullAccess")
        else:
            print(f"[FAIL] {domain}：查询失败 {e.status_code} {e.error_code} {e.error_msg}")
        return False

    name = current.name or domain
    if (current.type or "").upper() != "A":
        print(f"[FAIL] {name}：记录类型为 {current.type}，本工具仅支持更新 A 记录")
        return False

    old_values = current.records or []
    if old_values == [new_ip]:
        print(f"[SKIP] {name}：当前值已是 {new_ip}，无需更新")
        return True

    body = UpdateRecordSetReq()
    # 使用接口返回的记录名，避免大小写或末尾的点不一致导致更新失败
    body.name = name
    body.type = "A"
    body.records = [new_ip]
    # 保留记录原有 TTL，不强行改写用户配置
    body.ttl = current.ttl or 300

    try:
        req = UpdateRecordSetRequest()
        req.zone_id = zone_id
        req.recordset_id = record_id
        req.body = body
        client.update_record_set(req)
    except exceptions.ClientRequestException as e:
        print(f"[FAIL] {name}：更新失败 {e.status_code} {e.error_code} {e.error_msg}")
        return False

    print(f"[OK] {name}：{','.join(old_values) or '(空)'} -> {new_ip}（TTL {body.ttl}）")
    return True


def main():
    ak = os.getenv("HUAWEI_AK")
    sk = os.getenv("HUAWEI_SK")
    project_id = os.getenv("PROJECT_ID")
    region_id = (os.getenv("HUAWEI_REGION") or "").strip() or "cn-north-4"
    new_ip = (os.getenv("BEST_IP") or "").strip()

    missing = [
        name
        for name, val in (
            ("HUAWEI_AK", ak),
            ("HUAWEI_SK", sk),
            ("PROJECT_ID", project_id),
            ("BEST_IP", new_ip),
        )
        if not val
    ]
    if missing:
        print(f"[FATAL] 缺少必要环境变量：{', '.join(missing)}")
        sys.exit(1)

    if not IPV4_RE.match(new_ip):
        print(f"[FATAL] BEST_IP 不是合法 IPv4 地址：[{new_ip}]")
        sys.exit(1)

    records = dedupe(load_records())
    client = build_client(ak, sk, project_id, region_id)

    print(f"[i] 区域：{region_id} | 目标 IP：{new_ip} | 待处理：{len(records)} 条")
    success = 0
    for rec in records:
        if update_one(client, rec, new_ip):
            success += 1

    print(f"[i] 任务结束：成功 {success}/{len(records)}")
    sys.exit(0 if success == len(records) else 1)


if __name__ == "__main__":
    main()
