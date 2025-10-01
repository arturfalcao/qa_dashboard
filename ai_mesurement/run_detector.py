#!/usr/bin/env python3
"""
Script simples para executar o detector de defeitos
"""

from universal_defect_detector_final import UniversalDefectDetectorFinal
from pathlib import Path
import json

def run():
    print("\n" + "="*60)
    print("🔍 DETECTOR UNIVERSAL DE DEFEITOS")
    print("="*60)

    # Caminhos das imagens
    golden_image = "/home/celso/projects/qa_dashboard/test_images_mesurements/semburaco.jpg"
    test_image = "/home/celso/projects/qa_dashboard/test_images_mesurements/buraco.jpg"
    output_image = "/home/celso/projects/qa_dashboard/ai_mesurement/resultado_defeitos.png"

    print(f"\n📁 Imagem referência (sem defeito): {golden_image}")
    print(f"📁 Imagem a testar (com defeito): {test_image}")

    # Criar detector
    print("\n⚙️ Iniciando detector...")
    detector = UniversalDefectDetectorFinal()

    # Executar detecção
    print("\n🔍 Procurando defeitos...")
    result = detector.detect_defects(golden_image, test_image, output_image)

    if result and result['total_defects'] > 0:
        print(f"\n✅ SUCESSO! Encontrados {result['total_defects']} defeitos")

        # Mostrar top 5 defeitos
        print("\n📍 Localização dos principais defeitos:")
        for i, defect in enumerate(result['defects'][:5], 1):
            print(f"\n  {i}. Defeito #{i}")
            print(f"     📍 Posição: ({defect['center'][0]}, {defect['center'][1]})")
            print(f"     📏 Tamanho: {defect['bbox'][2]}x{defect['bbox'][3]} pixels")
            print(f"     🎯 Método: {defect['method']}")
            print(f"     ✅ Confiança: {defect['confidence']:.0%}")

        # Salvar relatório
        report_path = Path(output_image).with_suffix('.json')
        with open(report_path, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n📄 Relatório completo salvo em: {report_path}")
        print(f"🖼️ Imagem com marcações salva em: {output_image}")

    else:
        print("\n❌ Nenhum defeito encontrado")

    print("\n" + "="*60)
    print("✨ Processamento concluído!")
    print("="*60)

if __name__ == "__main__":
    run()