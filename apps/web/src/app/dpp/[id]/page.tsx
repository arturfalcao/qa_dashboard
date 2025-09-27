import { apiClient } from '@/lib/api'
import { notFound } from 'next/navigation'

interface DppPageProps {
  params: {
    id: string
  }
}

export default async function DppPage({ params }: DppPageProps) {
  try {
    const dpp = await apiClient.getPublicDpp(params.id)

    const materials = dpp.materials || []
    const certifications = dpp.certifications || []
    const metadata = dpp.metadata || {}
    const sustainabilityHighlights = metadata.sustainabilityHighlights || []

    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 py-8 px-4">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="bg-white rounded-2xl shadow-xl mb-8 p-8 text-center">
            <div className="mb-4">
              <div className="inline-block px-4 py-2 bg-emerald-100 text-emerald-800 text-sm font-medium rounded-full mb-4">
                Digital Product Passport
              </div>
            </div>
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              {dpp.brand} {dpp.styleRef}
            </h1>
            <p className="text-gray-600 text-lg">
              SKU: {dpp.productSku || 'N/A'}
            </p>
            {dpp.gtin && (
              <p className="text-gray-600">GTIN: {dpp.gtin}</p>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Product Information */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
                <div className="w-2 h-8 bg-blue-500 rounded mr-3"></div>
                Product Information
              </h2>
              <div className="space-y-4">
                <div className="flex justify-between">
                  <span className="font-medium text-gray-700">Brand:</span>
                  <span className="text-gray-900">{dpp.brand || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium text-gray-700">Style Reference:</span>
                  <span className="text-gray-900">{dpp.styleRef || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium text-gray-700">SKU:</span>
                  <span className="text-gray-900">{dpp.productSku || 'N/A'}</span>
                </div>
                {dpp.gtin && (
                  <div className="flex justify-between">
                    <span className="font-medium text-gray-700">GTIN:</span>
                    <span className="text-gray-900">{dpp.gtin}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Materials */}
            {materials.length > 0 && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
                  <div className="w-2 h-8 bg-green-500 rounded mr-3"></div>
                  Materials
                </h2>
                <div className="space-y-3">
                  {materials.map((material: any, index: number) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <span className="font-medium text-gray-900">
                          {material.fiber}
                        </span>
                        {material.properties?.certification && (
                          <div className="text-sm text-emerald-600 font-medium">
                            {material.properties.certification}
                          </div>
                        )}
                      </div>
                      <span className="text-lg font-bold text-blue-600">
                        {material.percentage}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Certifications */}
            {certifications.length > 0 && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
                  <div className="w-2 h-8 bg-emerald-500 rounded mr-3"></div>
                  Certifications
                </h2>
                <div className="grid grid-cols-1 gap-3">
                  {certifications.map((cert: any, index: number) => (
                    <div key={index} className="flex items-center p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                      <div className="w-3 h-3 bg-emerald-500 rounded-full mr-3"></div>
                      <span className="font-medium text-emerald-800">{cert.type}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Sustainability */}
            {sustainabilityHighlights.length > 0 && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
                  <div className="w-2 h-8 bg-green-500 rounded mr-3"></div>
                  Sustainability
                </h2>
                <div className="space-y-3">
                  {sustainabilityHighlights.map((highlight: string, index: number) => (
                    <div key={index} className="flex items-start p-3 bg-green-50 rounded-lg border border-green-200">
                      <div className="w-2 h-2 bg-green-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                      <span className="text-green-800">{highlight}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Traceability Score */}
            {metadata.traceabilityScore && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
                  <div className="w-2 h-8 bg-purple-500 rounded mr-3"></div>
                  Traceability
                </h2>
                <div className="text-center">
                  <div className="inline-block">
                    <div className="relative w-32 h-32 mb-4">
                      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                        <path
                          className="text-gray-300"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="3"
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        />
                        <path
                          className="text-purple-500"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="3"
                          strokeDasharray={`${metadata.traceabilityScore}, 100`}
                          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-2xl font-bold text-purple-600">
                          {metadata.traceabilityScore}%
                        </span>
                      </div>
                    </div>
                    <p className="text-gray-600">Traceability Score</p>
                  </div>
                </div>
              </div>
            )}

            {/* CO2 Footprint */}
            {metadata.co2FootprintKg && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
                  <div className="w-2 h-8 bg-orange-500 rounded mr-3"></div>
                  Carbon Footprint
                </h2>
                <div className="text-center">
                  <div className="text-4xl font-bold text-orange-600 mb-2">
                    {metadata.co2FootprintKg.toFixed(1)} kg
                  </div>
                  <p className="text-gray-600">Total CO₂ emissions</p>
                </div>
              </div>
            )}
          </div>

          {/* Download Links */}
          <div className="mt-8 bg-white rounded-xl shadow-lg p-6 text-center">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Download Options</h3>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href={`${process.env.NEXT_PUBLIC_API_BASE_URL}/dpp/${params.id}.json`}
                className="inline-flex items-center px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
                target="_blank"
                rel="noopener noreferrer"
              >
                Download JSON Data
              </a>
              <a
                href={`${process.env.NEXT_PUBLIC_API_BASE_URL}/dpp/${params.id}.pdf`}
                className="inline-flex items-center px-6 py-3 bg-gray-600 text-white font-medium rounded-lg hover:bg-gray-700 transition-colors"
                target="_blank"
                rel="noopener noreferrer"
              >
                Download PDF Report
              </a>
            </div>
          </div>

          {/* Footer */}
          <div className="mt-8 text-center text-gray-500 text-sm">
            <p>
              Digital Product Passport • Last updated: {new Date(dpp.updatedAt).toLocaleDateString()}
            </p>
            <p className="mt-2">
              This passport contains verified product information and supply chain data.
            </p>
          </div>
        </div>
      </div>
    )
  } catch (error) {
    console.error('Error fetching DPP:', error)
    notFound()
  }
}