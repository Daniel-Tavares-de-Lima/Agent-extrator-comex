# Eval SIMULADO (taxa de erro 3%). Não mede o Claude.

Conjuntos avaliados: 40

## Acerto por documento

| Documento | Acerto (todos os campos corretos) |
|---|---|
| invoice | 47.5% |
| packing_list | 65.0% |
| bl | 57.5% |

## Revisão humana

- Conjuntos enviados para revisão: 70.0%
- Defeitos injetados detectados: 10 de 10
- Conjuntos com algum erro de extração: 33
- **Erros de extração que passaram sem revisão: 6** (o número que mais importa)
- Falsos alarmes (extração perfeita, conjunto limpo, marcado para revisão): 0

## Acerto por campo (do pior para o melhor)

| Campo | Acerto |
|---|---|
| `bl.armador` | 85.0% |
| `invoice.itens[].quantidade` | 86.7% |
| `invoice.itens[].unidade` | 86.7% |
| `invoice.numero` | 87.5% |
| `invoice.itens[].total` | 87.5% |
| `invoice.itens[].preco_unitario` | 88.3% |
| `invoice.total_geral` | 90.0% |
| `invoice.exportador` | 90.0% |
| `invoice.data` | 90.0% |
| `invoice.importador` | 90.0% |
| `invoice.itens[].descricao` | 90.0% |
| `invoice.moeda` | 90.0% |
| `invoice.incoterm` | 90.0% |
| `packing_list.peso_liquido_kg` | 92.5% |
| `packing_list.peso_bruto_kg` | 92.5% |
| `bl.notify` | 92.5% |
| `bl.consignee` | 92.5% |
| `bl.porto_carga` | 92.5% |
| `bl.conteineres[].numero` | 94.6% |
| `bl.conteineres[].lacre` | 94.6% |
| `packing_list.cubagem_m3` | 95.0% |
| `packing_list.invoice_numero` | 95.0% |
| `bl.volumes` | 95.0% |
| `bl.porto_descarga` | 95.0% |
| `bl.peso_bruto_kg` | 95.0% |
| `packing_list.volumes` | 97.5% |
| `packing_list.itens[].peso_liquido_kg` | 97.5% |
| `bl.numero` | 97.5% |
| `bl.data_embarque` | 97.5% |
| `bl.navio` | 97.5% |
| `bl.embarcador` | 97.5% |
| `packing_list.itens[].descricao` | 98.3% |
| `packing_list.itens[].quantidade` | 99.2% |
