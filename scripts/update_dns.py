import os
import sys
import json
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion
from huaweicloudsdkdns.v2 import *
from huaweicloudsdkcore.exceptions import exceptions

def update_dns_record(ak, sk, project_id, region_id, zone_id, record_id, domain_name, new_ip):
    try:
        credentials = BasicCredentials(ak, sk, project_id)
        client = DnsClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(DnsRegion.value_of(region_id)) \
            .build()

        # 构造更新请求
        request = UpdateRecordSetRequest()
        request.zone_id = zone_id
        request.recordset_id = record_id
        
        body = UpdateRecordSetReq()
        body.name = domain_name
        body.type = "A"
        body.records = [new_ip]
        body.ttl = 300
        
        request.body = body
        
        response = client.update_record_set(request)
        print(f"成功更新域名 {domain_name} 解析到 IP: {new_ip}")
        return True

    except exceptions.ClientRequestException as e:
        print(f"更新域名 {domain_name} 失败: {e.status_code}, {e.error_msg}")
        return False
    except Exception as e:
        print(f"更新域名 {domain_name} 发生错误: {str(e)}")
        return False

if __name__ == "__main__":
    AK = os.getenv("HUAWEI_AK")
    SK = os.getenv("HUAWEI_SK")
    PROJECT_ID = os.getenv("PROJECT_ID")
    REGION_ID = os.getenv("HUAWEI_REGION", "cn-north-4")
    NEW_IP = os.getenv("BEST_IP")
    
    # 尝试从 DNS_RECORDS JSON 字符串获取配置
    DNS_RECORDS_JSON = os.getenv("DNS_RECORDS")
    
    records_to_update = []
    
    if DNS_RECORDS_JSON:
        try:
            records_to_update = json.loads(DNS_RECORDS_JSON)
        except Exception as e:
            print(f"解析 DNS_RECORDS 失败: {str(e)}")
            sys.exit(1)
    else:
        # 回退到单记录模式
        ZONE_ID = os.getenv("ZONE_ID")
        RECORD_ID = os.getenv("RECORD_ID")
        DOMAIN_NAME = os.getenv("DOMAIN_NAME")
        if all([ZONE_ID, RECORD_ID, DOMAIN_NAME]):
            records_to_update = [{
                "zone_id": ZONE_ID,
                "record_id": RECORD_ID,
                "domain_name": DOMAIN_NAME
            }]

    if not records_to_update:
        print("未发现有效的 DNS 记录配置。")
        sys.exit(1)
        
    if not all([AK, SK, PROJECT_ID, NEW_IP]):
        print("缺少全局必要环境变量 (AK/SK/PROJECT_ID/BEST_IP)。")
        sys.exit(1)

    success_count = 0
    for record in records_to_update:
        if update_dns_record(
            AK, SK, PROJECT_ID, REGION_ID, 
            record["zone_id"], record["record_id"], record["domain_name"], 
            NEW_IP
        ):
            success_count += 1
            
    print(f"任务结束: 成功 {success_count}/{len(records_to_update)}")
    if success_count == 0:
        sys.exit(1)
