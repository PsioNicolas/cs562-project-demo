select cust, prod, avg(quant), max_quant
from sales
where year = 2020
group by cust, prod;