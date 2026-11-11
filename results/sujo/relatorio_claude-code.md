# Eval com Claude via Claude Code (modelo haiku, esforço low, modo auto)

Conjuntos avaliados: 6

## Acerto por documento

| Documento | Acerto (todos os campos corretos) |
|---|---|
| invoice | 100.0% |
| packing_list | 66.7% |
| bl | 0.0% |

## Revisão humana

- Conjuntos enviados para revisão: 33.3%
- Defeitos injetados detectados: 0 de 0
- Conjuntos com algum erro de extração: 6
- **Erros de extração que passaram sem revisão: 4** (o número que mais importa)
- Falsos alarmes (extração perfeita, conjunto limpo, marcado para revisão): 0

## Por tipo de PDF

| Tipo | Conjuntos | Conjuntos 100% corretos | Erros silenciosos |
|---|---|---|---|
| scan_leve | 2 | 0 | 2 |
| scan_pesado | 2 | 0 | 0 |
| tabela | 2 | 0 | 2 |

## Acerto por campo (do pior para o melhor)

| Campo | Acerto |
|---|---|
| `bl.navio` | 0.0% |
| `bl.conteineres[].lacre` | 80.0% |
| `packing_list.peso_bruto_kg` | 83.3% |
| `packing_list.itens[].quantidade` | 87.5% |
| `bl.conteineres[].numero` | 90.0% |
| `invoice.incoterm` | 100.0% |
| `invoice.itens[].descricao` | 100.0% |
| `invoice.itens[].preco_unitario` | 100.0% |
| `invoice.importador` | 100.0% |
| `invoice.itens[].total` | 100.0% |
| `invoice.itens[].unidade` | 100.0% |
| `invoice.numero` | 100.0% |
| `invoice.itens[].quantidade` | 100.0% |
| `invoice.data` | 100.0% |
| `invoice.total_geral` | 100.0% |
| `invoice.exportador` | 100.0% |
| `invoice.moeda` | 100.0% |
| `packing_list.peso_liquido_kg` | 100.0% |
| `packing_list.cubagem_m3` | 100.0% |
| `packing_list.itens[].descricao` | 100.0% |
| `packing_list.volumes` | 100.0% |
| `packing_list.itens[].peso_liquido_kg` | 100.0% |
| `packing_list.invoice_numero` | 100.0% |
| `bl.consignee` | 100.0% |
| `bl.volumes` | 100.0% |
| `bl.numero` | 100.0% |
| `bl.data_embarque` | 100.0% |
| `bl.armador` | 100.0% |
| `bl.notify` | 100.0% |
| `bl.embarcador` | 100.0% |
| `bl.porto_carga` | 100.0% |
| `bl.porto_descarga` | 100.0% |
| `bl.peso_bruto_kg` | 100.0% |
