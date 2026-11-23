select c.chunk_id from chunks c join documents d using(doc_id)
where d.entity_id in ('EDJ','MS','SCHW','BAC','MER','RJF') and d.doc_type in ('10-K','10-Q','supplement','press','monthly','deck') and (
 (c.text ~* '(financial|wealth) advisors|advisors|representatives' and c.text ~ '[0-9],[0-9]{3}') or
 (c.text ~* 'net new (client )?assets|net client (aum )?flows|\mNNA\M' and c.text ~ '[0-9]') or
 (c.text ~* 'client assets|assets under (care|administration|management)|client balances' and c.text ~ '[0-9]'));
