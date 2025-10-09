# 🔧 Correção URGENTE: Enums de Relatórios em Produção

## 🚨 Erro em Produção

**Erro:** `Failed to generate report: Report generation failed: invalid input value for enum reports_status_enum: "GENERATING"`

## 📋 Problemas Identificados

### 1. Enum `reports_status_enum` incompleto ou ausente
- **Faltando:** `GENERATING`, `COMPLETED`, `EXPIRED`
- **Status:** Crítico - impede geração de relatórios

### 2. Enum `reports_type_enum` possivelmente incompleto
- **Faltando:** `DPP_SUMMARY`, `INLINE_QC_CHECKPOINTS`
- **Status:** Importante - impede alguns tipos de relatórios

## 🛠️ Solução Imediata para Produção

### Opção 1: Script SQL Direto (RECOMENDADO)

Execute o arquivo `/database/fix-production-enums.sql`:

```bash
# Na máquina de produção
psql -U postgres -d qa_dashboard -f fix-production-enums.sql
```

Ou execute diretamente:

```sql
-- COPIE E EXECUTE ESTE BLOCO EM PRODUÇÃO
BEGIN;

-- Criar/Atualizar reports_status_enum
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reports_status_enum') THEN
    CREATE TYPE "public"."reports_status_enum" AS ENUM (
      'PENDING',
      'READY',
      'FAILED',
      'GENERATING',
      'COMPLETED',
      'EXPIRED'
    );
  ELSE
    -- Adicionar valores faltantes
    ALTER TYPE "public"."reports_status_enum" ADD VALUE IF NOT EXISTS 'GENERATING';
    ALTER TYPE "public"."reports_status_enum" ADD VALUE IF NOT EXISTS 'COMPLETED';
    ALTER TYPE "public"."reports_status_enum" ADD VALUE IF NOT EXISTS 'EXPIRED';
  END IF;
END$$;

-- Criar/Atualizar reports_type_enum
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reports_type_enum') THEN
    CREATE TYPE "public"."reports_type_enum" AS ENUM (
      'MONTHLY_SCORECARD',
      'LOT',
      'EXECUTIVE_QUALITY_SUMMARY',
      'LOT_INSPECTION_REPORT',
      'MEASUREMENT_COMPLIANCE_SHEET',
      'PACKAGING_READINESS_REPORT',
      'SUPPLIER_PERFORMANCE_SNAPSHOT',
      'CAPA_REPORT',
      'INLINE_QC_CHECKPOINTS',
      'DPP_SUMMARY'
    );
  ELSE
    ALTER TYPE "public"."reports_type_enum" ADD VALUE IF NOT EXISTS 'INLINE_QC_CHECKPOINTS';
    ALTER TYPE "public"."reports_type_enum" ADD VALUE IF NOT EXISTS 'DPP_SUMMARY';
  END IF;
END$$;

COMMIT;

-- Verificar
SELECT enumlabel FROM pg_enum WHERE enumtypid =
  (SELECT oid FROM pg_type WHERE typname = 'reports_status_enum');
```

### Opção 2: Via Migrações TypeORM

```bash
# No servidor de produção
cd /path/to/qa_dashboard/apps/api

# Compilar
npm run build

# Executar migrações
npm run migration:run
```

## ✅ Verificação Pós-Correção

Execute estas queries para confirmar:

```sql
-- Deve retornar 6 valores: PENDING, READY, FAILED, GENERATING, COMPLETED, EXPIRED
SELECT enumlabel FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_status_enum')
ORDER BY enumsortorder;

-- Deve retornar 10 valores incluindo DPP_SUMMARY
SELECT enumlabel FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'reports_type_enum')
ORDER BY enumsortorder;
```

## 📊 Valores Esperados

### reports_status_enum (6 valores)
1. `PENDING` ✅
2. `READY` ✅
3. `FAILED` ✅
4. `GENERATING` ✅ **CRÍTICO - Causando erro atual**
5. `COMPLETED` ✅
6. `EXPIRED` ✅

### reports_type_enum (10 valores)
1. `MONTHLY_SCORECARD`
2. `LOT`
3. `EXECUTIVE_QUALITY_SUMMARY`
4. `LOT_INSPECTION_REPORT`
5. `MEASUREMENT_COMPLIANCE_SHEET`
6. `PACKAGING_READINESS_REPORT`
7. `SUPPLIER_PERFORMANCE_SNAPSHOT`
8. `CAPA_REPORT`
9. `INLINE_QC_CHECKPOINTS` ⚠️ **Pode estar faltando**
10. `DPP_SUMMARY` ⚠️ **Pode estar faltando**

## 🔍 Causa Raiz

As migrações que criam estes enums não foram executadas em produção:
- `1759300000000-AddDppSummaryReportType.ts`
- `1759400000000-AddReportStatusEnum.ts`

## 🚀 Prevenção Futura

1. **CI/CD Pipeline**: Adicionar execução automática de migrações no deploy
2. **Health Check**: Incluir verificação de enums no health endpoint
3. **Testes**: Adicionar testes que verificam sincronização código ↔️ banco

## 📝 Logs de Teste Local

```
Local executado com sucesso:
✅ reports_type_enum: 10 valores
✅ reports_status_enum: 6 valores
✅ reports_language_enum: 6 valores
```

## ⚡ Ação Imediata Necessária

**Execute o script SQL em produção AGORA para resolver o erro!**

```bash
psql -U <user> -h <host> -d qa_dashboard < fix-production-enums.sql
```

---

**Data:** 01/10/2025
**Severidade:** CRÍTICA - Sistema de relatórios parado
**Tempo estimado de correção:** < 1 minuto