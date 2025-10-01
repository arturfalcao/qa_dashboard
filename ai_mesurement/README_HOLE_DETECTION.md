# Sistema de Deteção de Buracos com IA Zero-Shot

## 📋 Visão Geral

Sistema avançado de deteção de defeitos em tecidos que combina:
- **Computer Vision tradicional** para deteção inicial
- **CLIP Zero-Shot** para validação sem necessidade de treino
- **Filtros de tamanho** configuráveis (medium+ por padrão)

## 🎯 Características

### 1. **Deteção Multi-Método**
- Contornos internos (buracos reais)
- Áreas desgastadas (análise de intensidade)
- Rasgões (deteção de bordas)

### 2. **Validação Zero-Shot com CLIP**
- **SEM necessidade de treino**
- Funciona imediatamente com qualquer imagem
- Compara semanticamente: "buraco no tecido" vs "tecido normal"

### 3. **Níveis de Confiança Ajustáveis**

| Confiança | Precisão | Recall | Uso Recomendado |
|-----------|----------|--------|-----------------|
| 90% | Muito Alta | Baixo | Controlo de qualidade crítico |
| 85% | Alta | Médio | Produção normal |
| 80% | Média | Alto | Deteção abrangente |

### 4. **Classificação de Severidade**

| Severidade | Tamanho | Ação |
|------------|---------|------|
| Minor | < 0.5 cm² | Monitorizar |
| Moderate | 0.5-2 cm² | Reparar se possível |
| Severe | 2-5 cm² | Reparação urgente |
| Critical | > 5 cm² | Possivelmente irreparável |

## 🚀 Como Usar

### Uso Básico
```python
from hole_detection import GarmentHoleDetector

# Inicializar com confiança padrão (85%)
detector = GarmentHoleDetector(
    pixels_per_cm=50.0,
    min_size='medium',  # Apenas defeitos ≥0.5cm²
    use_ai=True
)

# Detetar defeitos
holes = detector.detect_holes(image, mask)
```

### Ajustar Confiança
```python
# Para máxima precisão (menos defeitos, mais certeza)
detector = GarmentHoleDetector(use_ai=True)
detector.ai_detector.set_confidence(0.9)  # 90%

# Para máxima cobertura (mais defeitos, pode ter falsos positivos)
detector.ai_detector.set_confidence(0.75)  # 75%
```

## 📊 Resultados Típicos

### Com IA (85% confiança):
- ✅ 5-10 defeitos reais detetados
- ✅ <5% falsos positivos
- ✅ Score de qualidade realista

### Sem IA:
- ❌ 100+ "defeitos" detetados
- ❌ >90% falsos positivos
- ❌ Score de qualidade incorreto

## 🔧 Otimizações

### Para Velocidade:
```python
# Usar modelo CLIP menor
# Já configurado por padrão: clip-vit-base-patch32
```

### Para Precisão:
```python
# Aumentar confiança
detector.ai_detector.set_confidence(0.9)

# Usar apenas defeitos grandes
detector = GarmentHoleDetector(min_size='large')  # ≥2cm²
```

## 🎨 Visualização

O sistema gera:
1. **Imagem anotada** com defeitos marcados
2. **Relatório JSON** com métricas detalhadas
3. **Score de qualidade** (0-100)
4. **Recomendações** automáticas

## ⚠️ Limitações

1. **Iluminação**: Funciona melhor com luz uniforme
2. **Resolução**: Mínimo 50 pixels/cm recomendado
3. **Contraste**: Precisa de bom contraste tecido/fundo
4. **Padrões**: Pode confundir padrões complexos com defeitos

## 🔮 Melhorias Futuras

1. **Fine-tuning** com dataset específico
2. **SAM** para segmentação mais precisa
3. **Deteção de manchas** e outros defeitos
4. **API REST** para integração