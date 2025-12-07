"use client";

import dynamic from "next/dynamic";

const AlaskaMap = dynamic(() => import("./MapClient"), {
  ssr: false,
});

export default function MapPage() {
  return (
    <main style={{ width: "100%", height: "100vh" }}>
      <AlaskaMap />
    </main>
  );
}
