from app.extraction.schemas import MetricSpec


METRIC_REGISTRY = {

    # ==========================
    # 输出功率密度
    # ==========================

    "power_density": MetricSpec(
        key="power_density",

        display_name="输出功率密度",

        description=(
            "器件自身产生的输出功率除以有效面积。"
        ),

        search_queries=[
            "maximum output power density",
            "peak output power density",
            "power density under load resistance",
            "maximum power density of the device",
        ],

        canonical_unit="W/m²",

        valid_units=[
            "W/m²",
            "mW/m²",
            "μW/m²",
            "W/cm²",
            "mW/cm²",
            "μW/cm²",
        ],

        exclude_terms=[
            "energy density",
            "current density",
            "incident light power density",
            "illumination power density",
            "solar simulator",
            "PCE",
        ],
    ),

    # ==========================
    # 储能密度
    # ==========================

    "energy_density": MetricSpec(
        key="energy_density",

        display_name="储能密度",

        description=(
            "材料或器件单位体积储存或释放的电能。"
        ),

        search_queries=[
            "maximum energy density",
            "energy storage density",
            "discharged energy density",
            "stored energy density",
        ],

        canonical_unit="J/cm³",

        valid_units=[
            "J/cm³",
            "mJ/cm³",
            "J/m³",
        ],

        exclude_terms=[
            "power density",
        ],
    ),

    # ==========================
    # 击穿场强
    # ==========================

    "breakdown_strength": MetricSpec(
        key="breakdown_strength",

        display_name="击穿场强",

        description=(
            "介电材料发生电击穿时对应的最大电场强度。"
        ),

        search_queries=[
            "maximum breakdown field",
            "breakdown strength",
            "breakdown electric field",
        ],

        canonical_unit="MV/m",

        valid_units=[
            "MV/m",
            "kV/mm",
            "kV/cm",
            "V/μm",
        ],

        exclude_terms=[],
    ),

    # ==========================
    # 输出电压
    # ==========================

    "output_voltage": MetricSpec(
        key="output_voltage",

        display_name="输出电压",

        description=(
            "能量采集器件在给定实验条件下产生的输出电压。"
        ),

        search_queries=[
            "maximum output voltage",
            "open circuit voltage",
            "open-circuit voltage",
            "output voltage",
        ],

        canonical_unit="V",

        valid_units=[
            "V",
            "mV",
            "kV",
        ],

        exclude_terms=[
            "input voltage",
            "charging voltage",
        ],
    ),
}


def get_metric_spec(
    metric_name: str,
) -> MetricSpec:

    if metric_name not in METRIC_REGISTRY:
        raise ValueError(
            f"未知指标：{metric_name}"
        )

    return METRIC_REGISTRY[metric_name]