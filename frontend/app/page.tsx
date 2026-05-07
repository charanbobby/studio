import { PromptForm } from "@/components/PromptForm";

export default function Home() {
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-2">New Reel</h2>
      <p className="text-neutral-400 mb-6 text-sm">
        Type a brief; review the plan scene-by-scene; approve to generate.
      </p>
      <PromptForm />
    </div>
  );
}
