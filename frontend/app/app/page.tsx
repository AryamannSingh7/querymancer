import { Suspense } from "react";
import QuerymancerApp from "@/components/QuerymancerApp";

export default function Page() {
  return (
    <Suspense fallback={null}>
      <QuerymancerApp />
    </Suspense>
  );
}
