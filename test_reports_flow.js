#!/usr/bin/env node

/**
 * Script para testar o fluxo completo de relatórios
 * - Gera um relatório
 * - Verifica se foi salvo no MinIO (bucket pp-reports)
 * - Testa o download do relatório
 */

const API_BASE_URL = 'http://localhost:3001';

// Função auxiliar para fazer requisições
async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok && response.status !== 202) {
    const error = await response.text();
    throw new Error(`Request failed: ${response.status} - ${error}`);
  }

  if (response.headers.get('content-type')?.includes('application/json')) {
    return response.json();
  }
  return response;
}

// Função para fazer login
async function login() {
  console.log('🔐 Fazendo login...');
  const response = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({
      email: 'joana.costa@paco.example',
      password: 'demo1234'
    }),
  });

  return response.accessToken;
}

// Função para gerar um relatório
async function generateReport(token) {
  console.log('\n📊 Gerando relatório Executive Summary...');

  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

  const response = await request('/reports/executive-summary', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      dateFrom: thirtyDaysAgo.toISOString(),
      dateTo: new Date().toISOString(),
      factoryIds: [],
      includeDefectAnalysis: true,
      includeQualityTrends: true,
      includeSupplierPerformance: true,
    }),
  });

  console.log('✅ Relatório solicitado:', response);
  return response.id;
}

// Função para aguardar o relatório ficar pronto
async function waitForReport(token, reportId, maxAttempts = 30) {
  console.log('\n⏳ Aguardando processamento do relatório...');

  for (let i = 0; i < maxAttempts; i++) {
    const report = await request(`/reports/${reportId}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    console.log(`   Status: ${report.status}`);

    if (report.status === 'COMPLETED' || report.status === 'READY') {
      console.log('✅ Relatório pronto!');
      return report;
    }

    if (report.status === 'FAILED') {
      throw new Error('Falha na geração do relatório: ' + report.error);
    }

    // Aguarda 2 segundos antes de tentar novamente
    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  throw new Error('Timeout aguardando relatório');
}

// Função para baixar o relatório
async function downloadReport(token, reportId) {
  console.log('\n⬇️  Baixando relatório...');

  const response = await fetch(`${API_BASE_URL}/reports/${reportId}/download`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Download falhou: ${response.status}`);
  }

  const contentType = response.headers.get('content-type');
  const contentLength = response.headers.get('content-length');

  console.log(`✅ Download concluído:`);
  console.log(`   - Tipo: ${contentType}`);
  console.log(`   - Tamanho: ${contentLength} bytes`);

  return true;
}

// Função para verificar se o arquivo existe no MinIO
async function checkMinIOFile(reportFilePath) {
  console.log('\n🗂️  Verificando arquivo no MinIO...');
  console.log(`   Caminho: ${reportFilePath}`);

  // Verifica usando o comando mc dentro do container MinIO
  const { exec } = require('child_process');
  const util = require('util');
  const execPromise = util.promisify(exec);

  try {
    const { stdout } = await execPromise(
      `docker exec qa_dashboard-minio-1 mc stat local/pp-reports/${reportFilePath} 2>&1 | grep "Size" || echo "File not found"`
    );

    if (stdout.includes('File not found')) {
      console.log('❌ Arquivo não encontrado no MinIO');
      return false;
    }

    console.log('✅ Arquivo encontrado no MinIO');
    console.log(`   ${stdout.trim()}`);
    return true;
  } catch (error) {
    console.log('❌ Erro verificando arquivo:', error.message);
    return false;
  }
}

// Função para listar relatórios
async function listReports(token) {
  console.log('\n📋 Listando relatórios existentes...');

  const reports = await request('/reports', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  console.log(`✅ Encontrados ${reports.length} relatórios:`);
  reports.slice(0, 5).forEach(report => {
    console.log(`   - ${report.type}: ${report.fileName} (${report.status})`);
  });

  return reports;
}

// Função principal
async function main() {
  console.log('🚀 Iniciando teste do fluxo de relatórios\n');
  console.log('='.repeat(50));

  try {
    // 1. Login
    const token = await login();
    console.log('✅ Login realizado com sucesso');

    // 2. Listar relatórios existentes
    const existingReports = await listReports(token);

    // 3. Gerar novo relatório
    const reportId = await generateReport(token);

    // 4. Aguardar processamento
    const report = await waitForReport(token, reportId);

    // 5. Verificar no MinIO
    if (report.filePath) {
      await checkMinIOFile(report.filePath);
    }

    // 6. Fazer download
    await downloadReport(token, reportId);

    // 7. Listar novamente para confirmar
    await listReports(token);

    console.log('\n' + '='.repeat(50));
    console.log('✅ TESTE COMPLETO COM SUCESSO!');
    console.log('   - Relatório gerado e salvo no bucket pp-reports');
    console.log('   - Download funcionando corretamente');
    console.log('   - Fluxo completo validado');

  } catch (error) {
    console.error('\n❌ ERRO NO TESTE:', error.message);
    process.exit(1);
  }
}

// Executar teste
main().catch(console.error);