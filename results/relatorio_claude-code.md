# Eval com Claude via Claude Code (modelo haiku, esforço low, modo auto)

Conjuntos avaliados: 10

## Acerto por documento

| Documento | Acerto (todos os campos corretos) |
|---|---|
| invoice | 100.0% |
| packing_list | 100.0% |
| bl | 100.0% |

## Revisão humana

- Conjuntos enviados para revisão: 20.0%
- Defeitos injetados detectados: 2 de 2
- Conjuntos com algum erro de extração: 0
- **Erros de extração que passaram sem revisão: 0** (o número que mais importa)
- Falsos alarmes (extração perfeita, conjunto limpo, marcado para revisão): 0

## Acerto por campo (do pior para o melhor)

| Campo | Acerto |
|---|---|
| `invoice.incoterm` | 100.0% |
| `invoice.data` | 100.0% |
| `invoice.itens[].unidade` | 100.0% |
| `invoice.numero` | 100.0% |
| `invoice.moeda` | 100.0% |
| `invoice.itens[].descricao` | 100.0% |
| `invoice.itens[].total` | 100.0% |
| `invoice.importador` | 100.0% |
| `invoice.itens[].quantidade` | 100.0% |
| `invoice.exportador` | 100.0% |
| `invoice.itens[].preco_unitario` | 100.0% |
| `invoice.total_geral` | 100.0% |
| `packing_list.itens[].peso_liquido_kg` | 100.0% |
| `packing_list.cubagem_m3` | 100.0% |
| `packing_list.volumes` | 100.0% |
| `packing_list.peso_bruto_kg` | 100.0% |
| `packing_list.itens[].descricao` | 100.0% |
| `packing_list.invoice_numero` | 100.0% |
| `packing_list.itens[].quantidade` | 100.0% |
| `packing_list.peso_liquido_kg` | 100.0% |
| `bl.conteineres[].lacre` | 100.0% |
| `bl.embarcador` | 100.0% |
| `bl.conteineres[].numero` | 100.0% |
| `bl.consignee` | 100.0% |
| `bl.numero` | 100.0% |
| `bl.volumes` | 100.0% |
| `bl.peso_bruto_kg` | 100.0% |
| `bl.navio` | 100.0% |
| `bl.notify` | 100.0% |
| `bl.armador` | 100.0% |
| `bl.porto_carga` | 100.0% |
| `bl.porto_descarga` | 100.0% |
| `bl.data_embarque` | 100.0% |
