#!/usr/bin/env python3
"""
Script para detectar defeitos comparando qualquer par de imagens
Uso: python detect_defects.py imagem_sem_defeito.jpg imagem_com_defeito.jpg
"""

import sys
from pathlib import Path
from universal_defect_detector_final import UniversalDefectDetectorFinal
import json

def main():
    # Verificar argumentos
    if len(sys.argv) < 3:
        print("\n🔍 DETECTOR UNIVERSAL DE DEFEITOS")
        print("=" * 60)
        print("\n📌 USO:")
        print("   python detect_defects.py <golden_image> <test_image>")
        print("\n📌 EXEMPLO:")
        print("   python detect_defects.py semburaco.jpg buraco.jpg")
        print("\n📌 USANDO IMAGENS DE TESTE:")
        print("   python detect_defects.py")
        print("\n" + "=" * 60)

        # Usar imagens de teste se não foram fornecidos argumentos
        golden = "/home/celso/projects/qa_dashboard/test_images_mesurements/semburaco.jpg"
        test = "/home/celso/projects/qa_dashboard/test_images_mesurements/buraco.jpg"
        print(f"\n✨ Usando imagens de teste padrão...")
    else:
        golden = sys.argv[1]
        test = sys.argv[2]

    # Verificar se arquivos existem
    if not Path(golden).exists():
        print(f"❌ Erro: Arquivo não encontrado: {golden}")
        return

    if not Path(test).exists():
        print(f"❌ Erro: Arquivo não encontrado: {test}")
        return

    # Nome do arquivo de saída
    output_name = Path(test).stem + "_defects.png"
    output = Path("ai_mesurement") / output_name if Path("ai_mesurement").exists() else Path(output_name)

    print(f"\n🔍 DETECTANDO DEFEITOS")
    print("=" * 60)
    print(f"📁 Golden (sem defeito): {golden}")
    print(f"📁 Test (analisar): {test}")
    print(f"💾 Resultado será salvo em: {output}")

    # Executar detector
    detector = UniversalDefectDetectorFinal()
    result = detector.detect_defects(golden, test, str(output))

    # Mostrar resultados
    if result and result['total_defects'] > 0:
        print(f"\n✅ ENCONTRADOS {result['total_defects']} DEFEITOS!")
        print("=" * 60)

        # Top 3 defeitos
        for i, defect in enumerate(result['defects'][:3], 1):
            print(f"\n🎯 Defeito #{i}:")
            print(f"   Posição: ({defect['center'][0]}, {defect['center'][1]})")
            print(f"   Tamanho: {defect['bbox'][2]}x{defect['bbox'][3]} px")
            print(f"   Método: {defect['method']}")

        # Salvar JSON
        json_path = Path(str(output).replace('.png', '.json'))
        with open(json_path, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n📸 Imagem salva: {output}")
        print(f"📄 Relatório JSON: {json_path}")

    else:
        print("\n✅ Nenhum defeito detectado - peças idênticas!")

    print("\n✨ Concluído!")

if __name__ == "__main__":
    main()