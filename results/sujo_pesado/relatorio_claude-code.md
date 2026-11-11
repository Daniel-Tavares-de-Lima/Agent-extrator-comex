# Eval com Claude via Claude Code (modelo haiku, esforço low, modo auto)

Conjuntos avaliados: 6

## Acerto por documento

| Documento | Acerto (todos os campos corretos) |
|---|---|
| invoice | 66.7% |
| packing_list | 0.0% |
| bl | 16.7% |

## Revisão humana

- Conjuntos enviados para revisão: 100.0%
- Defeitos injetados detectados: 1 de 1
- Conjuntos com algum erro de extração: 6
- **Erros de extração que passaram sem revisão: 0** (o número que mais importa)
- Falsos alarmes (extração perfeita, conjunto limpo, marcado para revisão): 0

## Acerto por campo (do pior para o melhor)

| Campo | Acerto |
|---|---|
| `bl.conteineres[].numero` | 63.6% |
| `packing_list.peso_bruto_kg` | 66.7% |
| `packing_list.itens[].quantidade` | 66.7% |
| `bl.conteineres[].lacre` | 72.7% |
| `invoice.data` | 83.3% |
| `invoice.itens[].preco_unitario` | 83.3% |
| `packing_list.itens[].peso_liquido_kg` | 83.3% |
| `bl.embarcador` | 83.3% |
| `bl.numero` | 83.3% |
| `invoice.itens[].total` | 88.9% |
| `invoice.itens[].quantidade` | 94.4% |
| `invoice.itens[].descricao` | 94.4% |
| `packing_list.itens[].descricao` | 94.4% |
| `invoice.exportador` | 100.0% |
| `invoice.numero` | 100.0% |
| `invoice.moeda` | 100.0% |
| `invoice.total_geral` | 100.0% |
| `invoice.itens[].unidade` | 100.0% |
| `invoice.importador` | 100.0% |
| `invoice.incoterm` | 100.0% |
| `packing_list.cubagem_m3` | 100.0% |
| `packing_list.invoice_numero` | 100.0% |
| `packing_list.volumes` | 100.0% |
| `packing_list.peso_liquido_kg` | 100.0% |
| `bl.peso_bruto_kg` | 100.0% |
| `bl.porto_descarga` | 100.0% |
| `bl.navio` | 100.0% |
| `bl.notify` | 100.0% |
| `bl.volumes` | 100.0% |
| `bl.data_embarque` | 100.0% |
| `bl.consignee` | 100.0% |
| `bl.porto_carga` | 100.0% |
| `bl.armador` | 100.0% |
