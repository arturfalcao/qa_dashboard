# 🔧 PHOTO ACCESS FIX - SUMMARY

## ❌ PROBLEMA IDENTIFICADO

As fotos foram carregadas para DigitalOcean Spaces (produção), mas a API estava configurada para usar MinIO local. Além disso, os caminhos dos ficheiros na base de dados estavam incorretos.

### Detalhes do Problema:

1. **API configurada para MinIO local**:
   - Endpoint: `localhost:9000`
   - As fotos reais estavam em: `lon1.digitaloceanspaces.com`

2. **Caminhos incorretos na base de dados**:
   - `file_path` continha: `/tmp/qa_inspection_photos/piece_XXX_photo_X.jpg`
   - Devia conter: `inspections/{LOT_ID}/piece_XXX_photo_X.jpg`

3. **Controller a gerar URLs presigned errados**:
   - O controller chamava `storageService.getPresignedDownloadUrl(photo.filePath)`
   - O `filePath` apontava para o caminho local
   - O MinIO tentava gerar URL presigned no bucket local (que não existe)

---

## ✅ SOLUÇÕES APLICADAS

### 1. Configuração da API para DigitalOcean Spaces

**Ficheiros alterados**:
- `/home/celso/projects/qa_dashboard/apps/api/.env`
- `/home/celso/projects/qa_dashboard/.env`

**Alterações**:
```bash
# ANTES (MinIO Local)
MINIO_ENDPOINT=localhost
MINIO_PORT=9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_USE_SSL=false

# DEPOIS (DigitalOcean Spaces)
MINIO_ENDPOINT=lon1.digitaloceanspaces.com
MINIO_PORT=443
MINIO_ACCESS_KEY=DO004MPHJC2PFZVQE23M
MINIO_SECRET_KEY=WFoe83+YGGJkV/wQmtSJcxStddXp4pexdT7/0xXyvGQ
MINIO_USE_SSL=true
```

### 2. Correção dos Caminhos na Base de Dados

**Query SQL executada**:
```sql
UPDATE piece_photos
SET file_path = REPLACE(s3_url, 'https://pp-photos.lon1.digitaloceanspaces.com/', '')
WHERE s3_url LIKE 'https://pp-photos.lon1.digitaloceanspaces.com/inspections/%';
```

**Resultado**: 20 registos atualizados ✅

**Antes**:
```
file_path: /tmp/qa_inspection_photos/piece_001_photo_1_20251125_074816.jpg
s3_url: https://pp-photos.lon1.digitaloceanspaces.com/inspections/.../piece_001_photo_1_20251125_074816.jpg
```

**Depois**:
```
file_path: inspections/adb002da-571a-43e6-832d-75c9802aaa44/piece_001_photo_1_20251125_074816.jpg
s3_url: https://pp-photos.lon1.digitaloceanspaces.com/inspections/.../piece_001_photo_1_20251125_074816.jpg
```

---

## 🚀 PRÓXIMOS PASSOS

### Para que as fotos apareçam no frontend:

1. **Reiniciar a API** para carregar as novas variáveis de ambiente:
   ```bash
   cd /home/celso/projects/qa_dashboard
   pnpm dev
   # OU se já estiver a correr:
   pkill -f "nest start" && pnpm dev
   ```

2. **Verificar que a API está a correr**:
   ```bash
   curl http://localhost:3001/health
   ```

3. **Testar o endpoint de inspeção**:
   ```bash
   curl http://localhost:3001/inspection-sessions/a513d563-d465-4456-9fc6-be2cc2571531
   ```

   Deve retornar JSON com URLs presigned válidos para as fotos.

4. **Recarregar o frontend** (se já estiver a correr):
   - Abrir o browser
   - Recarregar a página com Ctrl+F5 (clear cache)
   - As imagens devem aparecer

---

## 🔍 COMO FUNCIONA AGORA

### Fluxo de acesso às fotos:

1. **Frontend** pede dados da sessão de inspeção
2. **API** recebe o pedido no `InspectionSessionController`
3. **Controller** itera sobre as fotos de cada peça
4. **StorageService** gera URL presigned usando:
   - Endpoint: `lon1.digitaloceanspaces.com`
   - Bucket: `pp-photos`
   - Key: `inspections/adb002da-571a-43e6-832d-75c9802aaa44/piece_XXX_photo_X.jpg`
5. **API** retorna JSON com URLs presigned válidos (válidos por 10 minutos)
6. **Frontend** renderiza as imagens usando esses URLs

### Exemplo de resposta da API:
```json
{
  "id": "a513d563-d465-4456-9fc6-be2cc2571531",
  "pieces": [
    {
      "id": "...",
      "pieceNumber": 1,
      "status": "ok",
      "photos": [
        {
          "id": "...",
          "url": "https://pp-photos.lon1.digitaloceanspaces.com/inspections/.../piece_001_photo_1.jpg?X-Amz-Algorithm=...",
          "capturedAt": "2025-11-25T07:48:16.000Z"
        }
      ]
    }
  ]
}
```

---

## 📊 VERIFICAÇÃO

### Fotos na Base de Dados:
```sql
SELECT
    ap.piece_number,
    ap.status,
    pp.file_path,
    pp.s3_url
FROM piece_photos pp
JOIN apparel_pieces ap ON ap.id = pp.piece_id
JOIN inspection_sessions iss ON iss.id = ap.inspection_session_id
WHERE iss.id = 'a513d563-d465-4456-9fc6-be2cc2571531'
ORDER BY ap.piece_number, pp.created_at;
```

### URLs Públicos Acessíveis:
- ✅ Piece #1: https://pp-photos.lon1.digitaloceanspaces.com/inspections/adb002da-571a-43e6-832d-75c9802aaa44/piece_001_photo_1_20251125_074816.jpg
- ✅ Piece #2: https://pp-photos.lon1.digitaloceanspaces.com/inspections/adb002da-571a-43e6-832d-75c9802aaa44/piece_002_photo_1_20251125_074817.jpg
- ✅ Piece #5 (DEFECT): https://pp-photos.lon1.digitaloceanspaces.com/inspections/adb002da-571a-43e6-832d-75c9802aaa44/piece_005_photo_1_20251125_074818.jpg

---

## ⚠️ NOTAS IMPORTANTES

1. **URLs Presigned vs URLs Públicos**:
   - As fotos têm ACL público, podem ser acedidas diretamente
   - A API gera URLs presigned para controlo de acesso
   - Ambos os métodos funcionam

2. **Bucket Permissions**:
   - O bucket `pp-photos` está configurado com `public-read`
   - Todas as fotos são públicas
   - CORS já deve estar configurado (verificar se necessário)

3. **Ambiente de Desenvolvimento**:
   - A configuração foi alterada para produção (DigitalOcean Spaces)
   - Se quiseres voltar ao MinIO local, reverte as alterações nos ficheiros `.env`

---

**Data da Correção**: 2025-11-25
**Sessão de Inspeção**: a513d563-d465-4456-9fc6-be2cc2571531
**Lote**: ZP-SS25-318 (Zara Portugal - Dress)
**Total de Fotos**: 20 (10 peças × 2 fotos cada)
**Status**: ✅ Configuração corrigida - Reiniciar API para aplicar
