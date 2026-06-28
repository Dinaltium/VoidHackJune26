import { useState, useEffect } from "react";
import type { Policy } from "@/lib/types";
import { MorphSurface } from "@/components/ui/morph-surface";
import { getRawPolicy, saveRawPolicy, askAiToEditPolicy } from "@/lib/api";
import { Pencil, Wrench, Sparkles, Save, AlertTriangle, Loader2 } from "lucide-react";

function ChipRow({ items, kind }: { items: string[]; kind: "deny" | "allow" | "" }) {
  return (
    <div className="chips">
      {items.map((item) => (
        <span className={`chip ${kind}`.trim()} key={item}>
          {item}
        </span>
      ))}
    </div>
  );
}

export function PolicyPanel({
  policy,
  onPolicyUpdated,
}: {
  policy: Policy | null;
  onPolicyUpdated?: (newPolicy: Policy) => void;
}) {
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"yaml" | "ai">("yaml");
  const [rawYaml, setRawYaml] = useState("");
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiExplanation, setAiExplanation] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [aiErrorMsg, setAiErrorMsg] = useState("");
  const [isValidating, setIsValidating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Fetch the latest raw policy YAML when the editor opens
  useEffect(() => {
    if (isEditorOpen) {
      setErrorMsg("");
      setAiErrorMsg("");
      setAiExplanation("");
      setAiPrompt("");
      setActiveTab("yaml");
      getRawPolicy()
        .then((res) => setRawYaml(res.yaml))
        .catch((err) => setErrorMsg(err.message || "Failed to load raw policy"));
    }
  }, [isEditorOpen]);

  const handleAiEdit = async () => {
    setIsValidating(true);
    setAiErrorMsg("");
    setAiExplanation("");
    setErrorMsg("");
    try {
      const res = await askAiToEditPolicy(aiPrompt);
      if (res.error) {
        setAiErrorMsg(res.error);
      } else {
        setRawYaml(res.yaml);
        setAiExplanation(res.explanation);
        setAiPrompt("");
        setActiveTab("yaml"); // Switch back to raw tab to preview changes
      }
    } catch (err: any) {
      setErrorMsg(err.message || "AI edit request failed");
    } finally {
      setIsValidating(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setErrorMsg("");
    try {
      const res = await saveRawPolicy(rawYaml);
      if (res.ok) {
        if (onPolicyUpdated) {
          onPolicyUpdated(res.policy);
        }
        setIsEditorOpen(false); // Close editor on success
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Save policy failed");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="panel relative">
      <div className="panel-head flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="panel-title">Active policy</h2>
          {policy ? (
            <span className="mono" style={{ color: "var(--faint)" }}>
              v{policy.version}
            </span>
          ) : null}
        </div>

        {policy && (
          <div className="flex items-center">
            <MorphSurface
              isOpen={isEditorOpen}
              onOpenChange={setIsEditorOpen}
              collapsedWidth={105}
              collapsedHeight={32}
              expandedWidth={640}
              expandedHeight={530}
              triggerLabel="Edit Policy"
              triggerIcon={<Pencil className="w-3 h-3" />}
              className="z-50 animate-fade-in"
              triggerClassName="px-2.5 py-1 text-xs border border-border/40 hover:bg-muted/50 rounded-full flex items-center gap-1 cursor-pointer transition-colors"
              renderIndicator={() => null}
              renderContent={() => (
                <div className="flex flex-col h-full text-foreground p-3 select-none">
                  {/* Header */}
                  <div className="flex items-center justify-between border-b pb-2 mb-2 border-border/40">
                    <div className="flex items-center gap-2">
                      <Wrench className="w-4 h-4 text-brand" />
                      <h3 className="font-semibold text-sm">Policy Editor</h3>
                    </div>
                    
                    {/* Tabs */}
                    <div className="flex bg-muted/60 p-0.5 rounded-lg border border-border/30 text-xs">
                      <button
                        type="button"
                        className={`px-3 py-1 rounded-md transition-all ${
                          activeTab === "yaml"
                            ? "bg-card text-foreground shadow-sm font-medium"
                            : "text-muted-foreground hover:text-foreground"
                        }`}
                        onClick={() => setActiveTab("yaml")}
                      >
                        YAML Raw
                      </button>
                      <button
                        type="button"
                        className={`px-3 py-1 rounded-md transition-all ${
                          activeTab === "ai"
                            ? "bg-card text-foreground shadow-sm font-medium"
                            : "text-muted-foreground hover:text-foreground"
                        }`}
                        onClick={() => setActiveTab("ai")}
                      >
                        AI Assist
                      </button>
                    </div>
                  </div>

                  {/* Tab Contents */}
                  <div className="flex-1 min-h-0 mb-3 relative flex flex-col">
                    {activeTab === "yaml" ? (
                      <textarea
                        value={rawYaml}
                        onChange={(e) => setRawYaml(e.target.value)}
                        spellCheck={false}
                        className="w-full flex-1 p-3 font-mono text-xs bg-muted/40 border border-border/40 rounded-lg outline-none resize-none focus:ring-1 focus:ring-brand/40 overflow-y-auto"
                        placeholder="# Loading policy..."
                        disabled={isValidating || isSaving}
                      />
                    ) : (
                      <div className="flex flex-col gap-3 flex-1">
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          Describe the security rules you want to change (e.g. <em>&quot;Deny tool run_code&quot;</em> or <em>&quot;Allow google.com egress&quot;</em>). The guarded AI assistant will safely generate the YAML changes.
                        </p>
                        
                        <textarea
                          value={aiPrompt}
                          onChange={(e) => setAiPrompt(e.target.value)}
                          placeholder="e.g., Allow read_logs tool and add api.github.com to egress allowlist"
                          className="w-full h-24 p-3 text-xs bg-muted/40 border border-border/40 rounded-lg outline-none resize-none focus:ring-1 focus:ring-brand/40"
                          disabled={isValidating || isSaving}
                        />

                        <button
                          type="button"
                          onClick={handleAiEdit}
                          disabled={isValidating || isSaving || !aiPrompt.trim()}
                          className="flex items-center justify-center gap-1.5 bg-brand hover:bg-brand/90 disabled:bg-muted-foreground/30 text-white font-medium text-xs py-2 px-4 rounded-lg transition-colors cursor-pointer"
                        >
                          {isValidating ? (
                            <>
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              Generating changes...
                            </>
                          ) : (
                            <>
                              <Sparkles className="w-3.5 h-3.5 text-yellow-300 fill-yellow-300" />
                              Apply AI Edit
                            </>
                          )}
                        </button>

                        {aiExplanation && (
                          <div className="text-[11px] p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400 leading-normal max-h-32 overflow-y-auto">
                            <strong>AI Change:</strong> {aiExplanation}
                          </div>
                        )}

                        {aiErrorMsg && (
                          <div className="text-[11px] p-2.5 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 leading-normal flex items-start gap-1.5 max-h-32 overflow-y-auto">
                            <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                            <div>
                              <strong>Guardrail Warning:</strong> {aiErrorMsg}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Errors / Footer Action Area */}
                  {errorMsg && (
                    <div className="text-[10px] py-1.5 px-2 bg-red-500/10 border border-red-500/25 rounded-md text-red-400 flex items-start gap-1.5 mb-2 leading-tight">
                      <AlertTriangle className="w-3 h-3 shrink-0 mt-0.5" />
                      <span>{errorMsg}</span>
                    </div>
                  )}

                  {/* Footer Controls */}
                  <div className="flex items-center justify-end gap-2 border-t pt-2 border-border/40 mt-auto">
                    <button
                      type="button"
                      onClick={() => setIsEditorOpen(false)}
                      className="px-3 py-1.5 rounded-lg border border-border/40 hover:bg-muted/50 text-xs transition-colors cursor-pointer disabled:opacity-50"
                      disabled={isValidating || isSaving}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleSave}
                      disabled={isValidating || isSaving || !rawYaml.trim()}
                      className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-xs py-1.5 px-3 rounded-lg transition-colors cursor-pointer"
                    >
                      {isSaving ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <Save className="w-3.5 h-3.5" />
                          Save Policy
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}
            />
          </div>
        )}
      </div>

      {policy === null ? (
        <p className="policy-desc">Policy unavailable — start the defender on :8000.</p>
      ) : (
        <>
          <p className="policy-desc">{policy.description}</p>

          <div className="policy-group">
            <div className="policy-label">Denied tools</div>
            <ChipRow items={policy.tool_denylist} kind="deny" />
          </div>
          <div className="policy-group">
            <div className="policy-label">Allowed tools</div>
            <ChipRow items={policy.tool_allowlist} kind="allow" />
          </div>
          <div className="policy-group">
            <div className="policy-label">Egress allowlist</div>
            <ChipRow items={policy.egress_allowlist} kind="" />
          </div>
          <div className="policy-group">
            <div className="policy-label">Limits</div>
            <ChipRow
              items={[
                `injection ≥ ${policy.injection_threshold}`,
                `budget ${policy.token_budget_per_session} tok`,
              ]}
              kind=""
            />
          </div>
        </>
      )}
    </div>
  );
}
