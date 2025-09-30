import { Controller, Get, Query, UseGuards } from "@nestjs/common";
import { ApiTags, ApiOperation } from "@nestjs/swagger";
import { JwtAuthGuard } from "../../auth/jwt-auth.guard";
import { RolesGuard } from "../../auth/roles.guard";
import { Roles } from "../../auth/roles.decorator";
import { CurrentUser } from "../../common/decorators";
import { LotService } from "../services/lot.service";
import { InspectionService } from "../services/inspection.service";
import { DefectService } from "../services/defect.service";
import { FactoryService } from "../services/factory.service";
import { InspectionSessionService } from "../services/inspection-session.service";
import { ApparelPieceService } from "../services/apparel-piece.service";
import { UserRole } from "@qa-dashboard/shared";

interface AuthUser {
  id: string;
  email: string;
  tenantId: string;
  roles: UserRole[];
}

@ApiTags("esg-reports")
@Controller("esg-reports")
@UseGuards(JwtAuthGuard, RolesGuard)
export class ESGReportsController {
  constructor(
    private readonly lotService: LotService,
    private readonly inspectionService: InspectionService,
    private readonly defectService: DefectService,
    private readonly factoryService: FactoryService,
    private readonly inspectionSessionService: InspectionSessionService,
    private readonly apparelPieceService: ApparelPieceService,
  ) {}

  @Get("impact-dashboard")
  @ApiOperation({ summary: "Get ESG impact dashboard metrics" })
  @Roles(UserRole.ADMIN, UserRole.OPS_MANAGER, UserRole.SUPERVISOR)
  async getImpactDashboard(
    @CurrentUser() user: AuthUser,
    @Query("startDate") startDate?: string,
    @Query("endDate") endDate?: string,
  ) {
    const lots = await this.lotService.findByTenantId(user.tenantId);

    // Filter by date range if provided
    const filteredLots = lots.filter((lot) => {
      if (startDate && new Date(lot.createdAt) < new Date(startDate))
        return false;
      if (endDate && new Date(lot.createdAt) > new Date(endDate)) return false;
      return true;
    });

    // Calculate total pieces inspected
    const totalPieces = filteredLots.reduce(
      (sum, lot) => sum + lot.quantityTotal,
      0,
    );

    // Calculate defect metrics
    const totalDefects = await this.defectService.countByTenantId(
      user.tenantId,
    );
    const defectRate =
      totalPieces > 0 ? (totalDefects / totalPieces) * 100 : 0;

    // Calculate waste metrics (assuming average garment weight of 0.2kg)
    const avgGarmentWeightKg = 0.2;
    const rejectedPieces = Math.round((totalDefects / 100) * totalPieces);
    const wasteKg = rejectedPieces * avgGarmentWeightKg;

    // Calculate carbon footprint (avg 5kg CO2 per kg textile waste)
    const co2PerKgWaste = 5;
    const carbonFootprintKg = wasteKg * co2PerKgWaste;

    // Calculate material efficiency
    const materialEfficiency =
      totalPieces > 0
        ? ((totalPieces - rejectedPieces) / totalPieces) * 100
        : 0;

    // Get certifications summary
    const factories = await this.factoryService.findAll();
    const certifiedFactories = factories.filter(
      (f) => f.certifications && f.certifications.length > 0,
    );
    const certificationRate =
      factories.length > 0
        ? (certifiedFactories.length / factories.length) * 100
        : 0;

    // Monthly trend (last 6 months)
    const monthlyTrend = await this.calculateMonthlyTrend(
      user.tenantId,
      filteredLots,
    );

    return {
      summary: {
        totalPieces,
        totalDefects,
        defectRate: Number(defectRate.toFixed(2)),
        rejectedPieces,
        wasteKg: Number(wasteKg.toFixed(2)),
        carbonFootprintKg: Number(carbonFootprintKg.toFixed(2)),
        materialEfficiency: Number(materialEfficiency.toFixed(2)),
        certificationRate: Number(certificationRate.toFixed(2)),
      },
      trend: monthlyTrend,
      period: {
        startDate: startDate || filteredLots[0]?.createdAt || null,
        endDate:
          endDate ||
          filteredLots[filteredLots.length - 1]?.createdAt ||
          null,
      },
    };
  }

  @Get("factory-scorecard")
  @ApiOperation({ summary: "Get factory ESG scorecard" })
  @Roles(UserRole.ADMIN, UserRole.OPS_MANAGER, UserRole.SUPERVISOR)
  async getFactoryScorecard(@CurrentUser() user: AuthUser) {
    const factories = await this.factoryService.findAll();
    const lots = await this.lotService.findByTenantId(user.tenantId);

    const scorecard = await Promise.all(
      factories.map(async (factory) => {
        // Get lots for this factory
        const factoryLots = lots.filter((lot) => lot.factoryId === factory.id);

        // Calculate quality score
        const avgDefectRate =
          factoryLots.length > 0
            ? factoryLots.reduce((sum, lot) => sum + lot.defectRate, 0) /
              factoryLots.length
            : 0;
        const qualityScore = Math.max(0, 100 - avgDefectRate);

        // Calculate material efficiency
        const totalPieces = factoryLots.reduce(
          (sum, lot) => sum + lot.quantityTotal,
          0,
        );
        const rejectedPieces = Math.round((avgDefectRate / 100) * totalPieces);
        const materialEfficiency =
          totalPieces > 0
            ? ((totalPieces - rejectedPieces) / totalPieces) * 100
            : 0;

        // Calculate compliance score (certifications)
        const certificationCount = factory.certifications?.length || 0;
        const complianceScore = Math.min(100, certificationCount * 20); // 20 points per cert, max 100

        // Calculate environmental score
        const wasteKg = rejectedPieces * 0.2; // avg garment weight
        const co2Kg = wasteKg * 5; // avg CO2 per kg waste
        const co2PerPiece = totalPieces > 0 ? co2Kg / totalPieces : 0;
        const environmentalScore = Math.max(
          0,
          100 - co2PerPiece * 100,
        ); // Lower CO2 = higher score

        // Calculate overall ESG score
        const esgScore =
          (qualityScore * 0.3 +
            materialEfficiency * 0.3 +
            complianceScore * 0.2 +
            environmentalScore * 0.2) /
          1;

        return {
          factoryId: factory.id,
          factoryName: factory.name,
          country: factory.country,
          city: factory.city,
          scores: {
            esg: Number(esgScore.toFixed(1)),
            quality: Number(qualityScore.toFixed(1)),
            materialEfficiency: Number(materialEfficiency.toFixed(1)),
            compliance: Number(complianceScore.toFixed(1)),
            environmental: Number(environmentalScore.toFixed(1)),
          },
          metrics: {
            totalLots: factoryLots.length,
            totalPieces,
            defectRate: Number(avgDefectRate.toFixed(2)),
            wasteKg: Number(wasteKg.toFixed(2)),
            co2Kg: Number(co2Kg.toFixed(2)),
            certifications: factory.certifications?.length || 0,
          },
          certifications:
            factory.certifications?.map((cert) => ({
              type: cert.certification,
              id: cert.id,
            })) || [],
        };
      }),
    );

    // Sort by ESG score descending
    return scorecard.sort((a, b) => b.scores.esg - a.scores.esg);
  }

  @Get("compliance-summary")
  @ApiOperation({ summary: "Get ISO compliance summary for audits" })
  @Roles(UserRole.ADMIN, UserRole.OPS_MANAGER, UserRole.SUPERVISOR)
  async getComplianceSummary(@CurrentUser() user: AuthUser) {
    const lots = await this.lotService.findByTenantId(user.tenantId);
    const factories = await this.factoryService.findAll();

    // ISO 9001 metrics (Quality Management)
    const totalLots = lots.length;
    const approvedLots = lots.filter((lot) => lot.status === "APPROVED").length;
    const rejectedLots = lots.filter((lot) => lot.status === "REJECTED").length;
    const avgDefectRate =
      lots.length > 0
        ? lots.reduce((sum, lot) => sum + lot.defectRate, 0) / lots.length
        : 0;

    // ISO 14001 metrics (Environmental Management)
    const totalPieces = lots.reduce((sum, lot) => sum + lot.quantityTotal, 0);
    const rejectedPieces = Math.round((avgDefectRate / 100) * totalPieces);
    const wasteKg = rejectedPieces * 0.2;
    const co2Kg = wasteKg * 5;

    // Certification tracking
    const certificationSummary = this.aggregateCertifications(factories);

    return {
      iso9001: {
        standard: "ISO 9001:2015",
        category: "Quality Management System",
        metrics: {
          totalLots,
          approvedLots,
          rejectedLots,
          approvalRate: Number(
            ((approvedLots / (totalLots || 1)) * 100).toFixed(2),
          ),
          avgDefectRate: Number(avgDefectRate.toFixed(2)),
        },
        status: avgDefectRate < 5 ? "COMPLIANT" : "REVIEW_REQUIRED",
      },
      iso14001: {
        standard: "ISO 14001:2015",
        category: "Environmental Management System",
        metrics: {
          totalPieces,
          rejectedPieces,
          wasteKg: Number(wasteKg.toFixed(2)),
          co2Kg: Number(co2Kg.toFixed(2)),
          wasteReductionRate: Number(
            ((1 - avgDefectRate / 100) * 100).toFixed(2),
          ),
        },
        status: avgDefectRate < 3 ? "COMPLIANT" : "IMPROVEMENT_NEEDED",
      },
      certifications: certificationSummary,
      generatedAt: new Date().toISOString(),
    };
  }

  @Get("material-efficiency")
  @ApiOperation({ summary: "Get material efficiency and waste analysis" })
  @Roles(UserRole.ADMIN, UserRole.OPS_MANAGER, UserRole.SUPERVISOR)
  async getMaterialEfficiency(@CurrentUser() user: AuthUser) {
    const lots = await this.lotService.findByTenantId(user.tenantId);

    const analysis = lots.map((lot) => {
      const totalPieces = lot.quantityTotal;
      const defectRate = lot.defectRate;
      const rejectedPieces = Math.round((defectRate / 100) * totalPieces);
      const acceptedPieces = totalPieces - rejectedPieces;

      const avgGarmentWeightKg = 0.2;
      const wasteKg = rejectedPieces * avgGarmentWeightKg;
      const co2Kg = wasteKg * 5;

      const materialEfficiency = (acceptedPieces / totalPieces) * 100;

      return {
        lotId: lot.id,
        styleRef: lot.styleRef,
        client: lot.client?.name,
        factory: lot.factory?.name,
        totalPieces,
        acceptedPieces,
        rejectedPieces,
        defectRate: Number(defectRate.toFixed(2)),
        materialEfficiency: Number(materialEfficiency.toFixed(2)),
        wasteKg: Number(wasteKg.toFixed(2)),
        co2Kg: Number(co2Kg.toFixed(2)),
        status: lot.status,
      };
    });

    // Calculate totals
    const totals = {
      totalPieces: analysis.reduce((sum, item) => sum + item.totalPieces, 0),
      acceptedPieces: analysis.reduce(
        (sum, item) => sum + item.acceptedPieces,
        0,
      ),
      rejectedPieces: analysis.reduce(
        (sum, item) => sum + item.rejectedPieces,
        0,
      ),
      wasteKg: analysis.reduce((sum, item) => sum + item.wasteKg, 0),
      co2Kg: analysis.reduce((sum, item) => sum + item.co2Kg, 0),
    };

    const overallEfficiency =
      totals.totalPieces > 0
        ? (totals.acceptedPieces / totals.totalPieces) * 100
        : 0;

    return {
      overview: {
        ...totals,
        overallEfficiency: Number(overallEfficiency.toFixed(2)),
        avgWastePerLot: Number(
          (totals.wasteKg / (lots.length || 1)).toFixed(2),
        ),
      },
      lots: analysis,
    };
  }

  @Get("carbon-footprint")
  @ApiOperation({ summary: "Get carbon footprint analysis" })
  @Roles(UserRole.ADMIN, UserRole.OPS_MANAGER, UserRole.SUPERVISOR)
  async getCarbonFootprint(@CurrentUser() user: AuthUser) {
    const lots = await this.lotService.findByTenantId(user.tenantId);

    // Calculate carbon from waste/defects
    const totalPieces = lots.reduce((sum, lot) => sum + lot.quantityTotal, 0);
    const avgDefectRate =
      lots.length > 0
        ? lots.reduce((sum, lot) => sum + lot.defectRate, 0) / lots.length
        : 0;
    const rejectedPieces = Math.round((avgDefectRate / 100) * totalPieces);
    const wasteKg = rejectedPieces * 0.2;
    const co2FromWaste = wasteKg * 5; // 5kg CO2 per kg textile waste

    // Calculate carbon from DPP metadata (if available)
    const co2FromDPP = lots.reduce((sum, lot) => {
      if (lot.dppMetadata?.co2FootprintKg) {
        return sum + lot.dppMetadata.co2FootprintKg;
      }
      return sum;
    }, 0);

    const totalCo2 = co2FromWaste + co2FromDPP;
    const co2PerPiece = totalPieces > 0 ? totalCo2 / totalPieces : 0;

    // Monthly breakdown
    const monthlyData = this.groupByMonth(lots).map((monthGroup) => {
      const monthPieces = monthGroup.lots.reduce(
        (sum, lot) => sum + lot.quantityTotal,
        0,
      );
      const monthDefects = monthGroup.lots.reduce(
        (sum, lot) => sum + (lot.defectRate / 100) * lot.quantityTotal,
        0,
      );
      const monthWaste = monthDefects * 0.2;
      const monthCo2 = monthWaste * 5;

      return {
        month: monthGroup.month,
        pieces: monthPieces,
        wasteKg: Number(monthWaste.toFixed(2)),
        co2Kg: Number(monthCo2.toFixed(2)),
      };
    });

    return {
      summary: {
        totalCo2Kg: Number(totalCo2.toFixed(2)),
        co2FromWaste: Number(co2FromWaste.toFixed(2)),
        co2FromProduction: Number(co2FromDPP.toFixed(2)),
        co2PerPiece: Number(co2PerPiece.toFixed(4)),
        totalPieces,
        wasteKg: Number(wasteKg.toFixed(2)),
      },
      monthlyBreakdown: monthlyData,
      recommendations: this.generateCarbonRecommendations(avgDefectRate),
    };
  }

  private async calculateMonthlyTrend(tenantId: string, lots: any[]) {
    const monthGroups = this.groupByMonth(lots);

    return monthGroups.map((group) => {
      const monthPieces = group.lots.reduce(
        (sum, lot) => sum + lot.quantityTotal,
        0,
      );
      const avgDefectRate =
        group.lots.length > 0
          ? group.lots.reduce((sum, lot) => sum + lot.defectRate, 0) /
            group.lots.length
          : 0;
      const rejectedPieces = Math.round((avgDefectRate / 100) * monthPieces);
      const wasteKg = rejectedPieces * 0.2;
      const co2Kg = wasteKg * 5;
      const materialEfficiency =
        monthPieces > 0 ? ((monthPieces - rejectedPieces) / monthPieces) * 100 : 0;

      return {
        month: group.month,
        pieces: monthPieces,
        defectRate: Number(avgDefectRate.toFixed(2)),
        wasteKg: Number(wasteKg.toFixed(2)),
        co2Kg: Number(co2Kg.toFixed(2)),
        materialEfficiency: Number(materialEfficiency.toFixed(2)),
      };
    });
  }

  private groupByMonth(lots: any[]) {
    const groups = new Map<string, any[]>();

    lots.forEach((lot) => {
      const date = new Date(lot.createdAt);
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;

      if (!groups.has(monthKey)) {
        groups.set(monthKey, []);
      }
      groups.get(monthKey)!.push(lot);
    });

    return Array.from(groups.entries())
      .sort((a, b) => a[0].localeCompare(b[0]))
      .slice(-6) // Last 6 months
      .map(([month, lots]) => ({ month, lots }));
  }

  private aggregateCertifications(factories: any[]) {
    const certMap = new Map<string, number>();

    factories.forEach((factory) => {
      if (factory.certifications) {
        factory.certifications.forEach((cert: any) => {
          const type = cert.certification;
          certMap.set(type, (certMap.get(type) || 0) + 1);
        });
      }
    });

    return Array.from(certMap.entries()).map(([type, count]) => ({
      type,
      count,
      percentage: Number(((count / factories.length) * 100).toFixed(1)),
    }));
  }

  private generateCarbonRecommendations(defectRate: number): string[] {
    const recommendations: string[] = [];

    if (defectRate > 5) {
      recommendations.push(
        "Critical: Defect rate above 5% - Implement immediate quality control improvements",
      );
      recommendations.push(
        "Review operator training programs to reduce defects at source",
      );
    }

    if (defectRate > 3) {
      recommendations.push(
        "Consider implementing inline inspection to catch defects earlier",
      );
    }

    if (defectRate < 2) {
      recommendations.push(
        "Excellent: Maintain current quality standards - Share best practices across factories",
      );
    }

    recommendations.push(
      "Track material suppliers with highest defect rates for targeted improvement",
    );
    recommendations.push(
      "Implement recycling program for rejected pieces to reduce carbon impact",
    );

    return recommendations;
  }
}