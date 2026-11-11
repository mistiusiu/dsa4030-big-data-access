import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import { ArrowRight } from "lucide-react";
import { Icon } from "@/components/Icon";
import { ModeTag, Page, PageHeader, Spinner, Tag } from "@/components/ui";
import { api } from "@/lib/api";
import { fmt } from "@/lib/format";
import type { DatasetCard } from "@/lib/types";

export default function Lake() {
  const { data, isLoading } = useQuery({
    queryKey: ["datasets"],
    queryFn: async () => (await api.get<DatasetCard[]>("/lake/datasets/")).data,
  });
  const domains = [...new Set(data?.map((d) => d.domain))];

  return (
    <>
      <PageHeader eyebrow="Data lake" title="Fourteen silos, one permission grid">
        Each dataset is a Parquet file queried live by DuckDB. What you get back depends on your role's
        cell in the grid — open a dataset to see exactly which columns are cleared, masked or removed.
      </PageHeader>
      <Page>
        {isLoading && <Spinner />}
        <div className="space-y-10">
          {domains.map((domain) => (
            <section key={domain}>
              <h2 className="mb-3 flex items-center gap-3 text-lg font-bold">
                <span className="h-5 w-1 bg-brand" /> {domain}
              </h2>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {data?.filter((d) => d.domain === domain).map((d) => (
                  <Link
                    key={d.slug}
                    to={`/lake/${d.slug}`}
                    className={clsx(
                      "card group flex flex-col p-5 text-ink no-underline transition-shadow hover:no-underline hover:shadow-raised",
                      d.mode === "deny" && "bg-gray-10/60",
                    )}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <span className={clsx("flex h-11 w-11 items-center justify-center rounded", d.mode === "deny" ? "bg-gray-20 text-gray-50" : "bg-ink text-white")}>
                        <Icon name={d.icon} size={22} />
                      </span>
                      <ModeTag mode={d.mode} />
                    </div>
                    <h3 className={clsx("mt-4 text-lg font-bold", d.mode === "deny" && "text-gray-60")}>{d.title}</h3>
                    <p className="mt-1 text-sm text-gray-60">{d.description}</p>
                    <p className="mt-3 border-l-2 border-gray-30 pl-3 text-sm italic text-ink-4">{d.rationale}</p>
                    <div className="mt-auto flex items-center gap-2 pt-4 text-xs text-gray-60">
                      <Tag>{d.rows != null ? `${fmt.format(d.rows)} rows` : "not generated"}</Tag>
                      <Tag>{d.columns} columns</Tag>
                      {d.mode === "aggregate" && d.min_group_size > 1 && <Tag tone="blue">k ≥ {d.min_group_size}</Tag>}
                      {d.cross_analyze && <Tag tone="purple">SQL</Tag>}
                      <ArrowRight size={16} className="ml-auto text-gray-40 transition-transform group-hover:translate-x-1 group-hover:text-brand" />
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      </Page>
    </>
  );
}
