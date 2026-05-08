select
    cust,
    sum(case when state = 'NY' then quant else 0 end) as sum_1_quant,
    sum(case when state = 'NJ' then quant else 0 end) as sum_2_quant,
from sales
group by cust
having sum(case when state = 'NY' then quant else 0 end) > sum(case when state = 'NJ' then quant else 0 end);