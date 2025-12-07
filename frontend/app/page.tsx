import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { HoverCardT } from "@/shadcn/HoverCard";
import { Item } from "@radix-ui/react-dropdown-menu";
import { ItemT } from "@/shadcn/ItemT";

export default function HomePage() {
  return (

<>
    <div>
      <HoverCardT/>
    </div>
    <main className="min-h-screen bg-background text-foreground">
      {/* Main */}
      <section className="mx-auto max-w-7xl px-6 py-24 text-center">
        {/* <Badge className="mb-6">Research Prototype</Badge> */}
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          TENeT
        </h1>

        <p className="mx-auto mt-6 max-w-3xl text-lg text-muted-foreground">
          A data-driven geospatial platform that identifies healthcare deserts
          across Alaska and evaluates real-world telehealth feasibility using
          broadband performance and connectivity data.
        </p>

        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Button size="lg" asChild>
            <Link href="/map">Launch Interactive Map</Link>
          </Button>

          <Button size="lg" variant="outline" asChild>
            <Link href="#methodology">View Methodology</Link>
          </Button>
        </div>
      </section>

      <Separator />

      {/* ================= PROBLEM / SOLUTION / IMPACT ================= */}
      <section className="mx-auto max-w-7xl px-6 py-20">
        <div className="grid gap-8 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Healthcare Access Crisis</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Many Alaskan villages face extreme barriers to medical care due to
              remoteness, seasonal transportation, workforce shortages, and
              limited medical infrastructure.
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Telehealth as a Bridge</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              This platform integrates healthcare facility availability with
              broadband performance to determine where telehealth can
              realistically replace in-person scarcity.
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Decision Support Tool</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Policymakers, universities, and health systems can use this tool to
              prioritize infrastructure investment and remote care deployment.
            </CardContent>
          </Card>
        </div>
      </section>

      <Separator />

      {/* Methdology */}
      <section
        id="methodology"
        className="mx-auto max-w-7xl px-6 py-20"
      >

        <div className="mt-10 flex gap-4 items-center-safe justify-center-safe">
          <Card>
            <CardHeader >
              <CardTitle className="text-red-500  dark:bg-blue-600">Features</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-2">
          <ItemT value={"AI Chatbot and Voice Assistant"} dest={"#"}/>
          
          <ItemT value={"Healthcare Desert Detection"} dest={"#"}/>
          <ItemT value={"Interactive First Map"} dest={"#"}/>
            </CardContent>
          </Card>
          {/* <ItemT value={"Reporting & Export"} dest={"#"}/> */}
        </div>
      </section>

      <Separator />

      {/* Data source for tenet */}
      <section className="mx-auto max-w-7xl px-6 py-20 text-center">
        <h2 className="text-3xl font-semibold">Data Sources</h2>

        <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
          This project integrates national open datasets with Alaska-specific
          infrastructure reporting.
        </p>

        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <Badge variant="secondary">FCC Broadband Maps</Badge>
          <Badge variant="secondary">ISP Network Telemetry</Badge>
          <Badge variant="secondary" className="bg-blue-500 text-white dark:bg-blue-600">TENeT AI</Badge>
          <Badge variant="secondary">Alaska Public Health Records</Badge>
        </div>
      </section>

      <Separator />

      {/* ================= CTA ================= */}
      <section className="mx-auto max-w-7xl px-6 py-24 text-center">
        <h2 className="text-3xl font-semibold">
          Explore Telehealth Opportunity Zones
        </h2>

        <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
          Interactively analyze healthcare deserts, broadband performance, and
          telehealth feasibility across cities and remote villages.
        </p>

        <div className="mt-8">
          <Button size="lg" asChild>
            <Link href="/map">Open Alaska Map</Link>
          </Button>
        </div>
      </section>

      {/* ================= FOOTER ================= */}
      <footer className="border-t py-8 text-center text-xs text-muted-foreground">
        Alaska Telehealth
      </footer>
    </main>
    </>
  );
}
