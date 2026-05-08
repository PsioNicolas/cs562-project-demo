select
    cust, 
    sum(case when state = 'NY' then quant else 0 end) as sum_1_quant,
    sum(case when state = 'NJ' then quant else 0 end) as sum_2_quant,
    max(case when state = 'CT' then quant end) as max_3_quant
from sales
group by cust;