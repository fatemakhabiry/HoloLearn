/// Models for the Research Agent API

/// A single finding section — content text + list of source URLs
class ResearchFinding {
  final String content;
  final List<String> sources;

  const ResearchFinding({
    required this.content,
    required this.sources,
  });

  factory ResearchFinding.fromJson(Map<String, dynamic> json) {
    return ResearchFinding(
      content: json['content']?.toString() ?? '',
      sources: (json['sources'] as List<dynamic>?)
              ?.map((s) => s.toString())
              .toList() ??
          [],
    );
  }
}

/// Full response from POST /research/agent
class ResearchResponse {
  final String question;

  /// Raw findings map — key is the section name e.g. 'background_context'
  final Map<String, ResearchFinding> findings;

  const ResearchResponse({
    required this.question,
    required this.findings,
  });

  factory ResearchResponse.fromJson(Map<String, dynamic> json) {
    final rawFindings =
        json['findings'] as Map<String, dynamic>? ?? {};

    final findings = rawFindings.map((key, value) {
      return MapEntry(
        key,
        ResearchFinding.fromJson(value as Map<String, dynamic>),
      );
    });

    return ResearchResponse(
      question: json['question']?.toString() ?? '',
      findings: findings,
    );
  }

  /// All source URLs deduplicated across all findings
  List<String> get allSources {
    final seen = <String>{};
    return findings.values
        .expand((f) => f.sources)
        .where((url) => seen.add(url))
        .toList();
  }

  /// Section title from snake_case key → readable label
  /// e.g. 'background_context' → 'Background Context'
  static String sectionLabel(String key) {
    return key
        .split('_')
        .map((w) => w.isEmpty
            ? ''
            : w[0].toUpperCase() + w.substring(1))
        .join(' ');
  }
}
