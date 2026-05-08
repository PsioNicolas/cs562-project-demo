select cust, count(quant)
from sales
where state = 'NY'
group by cust;