from typing import Generator

import polars as pl


from .partition import PartitionData


def breakout_partitions(
    df: pl.DataFrame,
    partition_cols: list[str],
    default_partitions: list[dict[str, str]] | None = None,
) -> Generator[PartitionData, None, None]:
    """Split a dataframe into partitions.

    The data in each partition will be written to storage as a separate parquet file.
    """
    parts = df.select(*partition_cols).unique().sort(*partition_cols).to_dicts()

    # Keep track of yielded partitions.
    # This is so we can guarantee full coverage of default_partitions list.
    yielded_partitions = []

    if len(df) == 0:
        assert default_partitions is not None
        for default_partition in default_partitions:
            partition_data = PartitionData.from_dict(
                partition_cols=partition_cols,
                partitions_dict=default_partition,
                df=df.drop(*partition_cols),
            )

            yielded_partitions.append(partition_data.partition.path)
            yield partition_data

    else:
        for part in parts:
            part_df = df.filter(pl.all_horizontal(pl.col(col) == val for col, val in part.items()))

            partition_data = PartitionData.from_dict(
                partition_cols=partition_cols,
                partitions_dict=part,
                df=part_df.drop(*partition_cols),
            )

            yielded_partitions.append(partition_data.partition.path)
            yield partition_data

    # The default partitions that are not observed on the actual data still need to
    # be yielded so that markers for them can be written out.

    for default_partition in default_partitions or []:
        default_partition_data = PartitionData.from_dict(
            partition_cols=partition_cols,
            partitions_dict=default_partition,
            df=df.filter(False).drop(*partition_cols),
        )

        if default_partition_data.partition.path not in yielded_partitions:
            yield default_partition_data
