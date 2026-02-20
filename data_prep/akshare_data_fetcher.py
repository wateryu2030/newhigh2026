#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 数据预处理工具
用于批量获取行业、财务、资金流数据，供策略使用
"""
import akshare as ak
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import time


class AKShareDataFetcher:
    """AKShare 数据获取器"""
    
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def get_industry_stocks(self, industry_name):
        """获取行业成分股"""
        try:
            # 获取行业板块信息
            industry_df = ak.stock_board_industry_name_em()
            # 筛选目标行业
            target = industry_df[industry_df["板块名称"].str.contains(industry_name, na=False)]
            if len(target) == 0:
                return []
            
            industry_code = target.iloc[0]["板块代码"]
            # 获取成分股
            stocks_df = ak.stock_board_industry_cons_em(symbol=industry_name)
            return stocks_df["代码"].tolist() if len(stocks_df) > 0 else []
        except Exception as e:
            print(f"获取行业 {industry_name} 成分股失败: {e}")
            return []
    
    def get_finance_data(self, stock_code, periods=4):
        """获取财务数据（营收/净利润增速）"""
        try:
            # 获取财务指标
            finance_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", 
                                          start_date="20200101", end_date="20251231", adjust="")
            if len(finance_df) == 0:
                return None
            
            # 获取财务报告数据（简化版，实际应使用财报接口）
            # 这里使用历史价格数据作为代理
            return {
                "revenue_growth": np.nan,  # 实际应从财报接口获取
                "profit_growth": np.nan,
            }
        except Exception as e:
            print(f"获取 {stock_code} 财务数据失败: {e}")
            return None
    
    def get_capital_flow(self, stock_code, days=20):
        """获取资金流数据（北向+主力资金）"""
        try:
            # 获取北向资金持仓
            try:
                north_df = ak.stock_hsgt_hold_detail_em(symbol=stock_code)
                if len(north_df) > 0:
                    north_change = north_df["持股数量"].pct_change(days).iloc[-1] * 100 if len(north_df) >= days else 0
                else:
                    north_change = 0
            except:
                north_change = 0
            
            # 获取主力资金（简化版）
            try:
                flow_df = ak.stock_fund_flow_individual(symbol=stock_code)
                if len(flow_df) > 0:
                    main_flow_ratio = flow_df["主力净流入"].head(days).mean() / flow_df["成交额"].head(days).mean() * 100 if len(flow_df) >= days else 0
                else:
                    main_flow_ratio = 0
            except:
                main_flow_ratio = 0
            
            return {
                "north_change": north_change,
                "main_flow_ratio": main_flow_ratio,
            }
        except Exception as e:
            print(f"获取 {stock_code} 资金流失败: {e}")
            return {"north_change": 0, "main_flow_ratio": 0}
    
    def prepare_industry_data(self):
        """准备行业数据（策略1使用）"""
        tech_industries = ["半导体", "计算机应用", "电力设备"]
        consume_industries = ["食品饮料", "美容护理", "白色家电"]
        target_industries = tech_industries + consume_industries
        
        industry_stock_map = {}
        industry_scores = {}
        
        for industry in target_industries:
            print(f"处理行业: {industry}")
            stocks = self.get_industry_stocks(industry)
            if len(stocks) == 0:
                continue
            
            industry_stock_map[industry] = stocks
            
            # 计算行业得分（简化版）
            scores = []
            for stock in stocks[:10]:  # 限制数量避免请求过多
                finance = self.get_finance_data(stock)
                flow = self.get_capital_flow(stock)
                if finance:
                    # 简化得分计算
                    score = 50  # 默认分
                    scores.append(score)
                time.sleep(0.1)  # 避免请求过快
            
            industry_scores[industry] = {
                "景气度得分": np.mean(scores) if scores else 50,
                "资金流得分": 50,  # 简化
                "综合得分": 50,
            }
        
        # 保存数据
        stock_map_df = pd.DataFrame({
            "行业名称": list(industry_stock_map.keys()),
            "股票代码": [",".join(stocks) for stocks in industry_stock_map.values()]
        })
        stock_map_df.to_csv(os.path.join(self.data_dir, "industry_stock_map.csv"), index=False, encoding="utf-8-sig")
        
        score_df = pd.DataFrame(industry_scores).T
        score_df.to_csv(os.path.join(self.data_dir, "industry_score.csv"), encoding="utf-8-sig")
        
        print(f"行业数据已保存到 {self.data_dir}/")
        return stock_map_df, score_df
    
    def prepare_leader_stocks(self):
        """准备龙头股票池（策略2使用）"""
        # 获取A股列表
        try:
            stock_list = ak.stock_info_a_code_name()
            # 筛选高科技和消费龙头（简化版，实际应基于市值、概念等筛选）
            tech_stocks = []
            consume_stocks = []
            
            # 这里简化处理，实际应从概念板块筛选
            tech_concepts = ["半导体", "人工智能", "算力"]
            consume_concepts = ["食品饮料", "美妆", "家电"]
            
            # 保存股票池
            pd.DataFrame({"代码": tech_stocks}).to_csv(
                os.path.join(self.data_dir, "tech_leader_stocks.csv"), index=False, encoding="utf-8-sig")
            pd.DataFrame({"代码": consume_stocks}).to_csv(
                os.path.join(self.data_dir, "consume_leader_stocks.csv"), index=False, encoding="utf-8-sig")
            
            print("龙头股票池已保存")
        except Exception as e:
            print(f"准备龙头股票池失败: {e}")


if __name__ == "__main__":
    fetcher = AKShareDataFetcher()
    print("开始准备行业数据...")
    fetcher.prepare_industry_data()
    print("数据准备完成！")
