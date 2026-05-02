import os
import sys
from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkdns.v2.region.dns_region import DnsRegion
from huaweicloudsdkdns.v2 import *
from huaweicloudsdkcore.exceptions import exceptions

def list_dns_info(ak, sk, project_id):
    try:
        region_id = os.getenv("HUAWEI_REGION", "cn-north-4")
        credentials = BasicCredentials(ak, sk, project_id)
        client = DnsClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(DnsRegion.value_of(region_id)) \
            .build()

        # 1. 列出公网 Zone
        print("\n--- 正在查询您的域名 (Zones) ---")
        request = ListPublicZonesRequest()
        response = client.list_public_zones(request)
        
        zones = response.zones
        if not zones:
            print("未找到任何公网域名，请确认您的域名已托管在华为云解析。")
            return

        for zone in zones:
            print(f"域名: {zone.name} | ZONE_ID: {zone.id}")
            
            # 2. 列出该 Zone 下的所有记录 (Record Sets)
            print(f"  --- 正在查询 {zone.name} 下的记录 (Record Sets) ---")
            rs_request = ListRecordSetsWithLineRequest(zone_id=zone.id)
            rs_response = client.list_record_sets_with_line(rs_request)
            
            for rs in rs_response.recordsets:
                # 显示 A, CNAME 记录供用户参考
                if rs.type in ["A", "CNAME"]:
                    print(f"    记录名: {rs.name} | 类型: {rs.type} | 当前值: {rs.records} | RECORD_ID: {rs.id}")

    except exceptions.ClientRequestException as e:
        print(f"请求失败: {e.status_code}, {e.request_id}, {e.error_code}, {e.error_msg}")
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    # 如果用户想在本地运行测试，可以手动填入或通过环境变量传入
    AK = os.getenv("HUAWEI_AK")
    SK = os.getenv("HUAWEI_SK")
    PROJECT_ID = os.getenv("PROJECT_ID") # 如果不知道可以先留空，某些接口可能需要
    
    if not AK or not SK:
        print("请设置环境变量 HUAWEI_AK 和 HUAWEI_SK")
    else:
        # 如果 Project ID 不知道，华为云 SDK 通常可以从 AK/SK 自动获取（取决于 Region）
        # 但显式指定更稳妥
        list_dns_info(AK, SK, PROJECT_ID if PROJECT_ID else "")
