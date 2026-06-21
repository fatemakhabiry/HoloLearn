/// Model for the lecture transcript feature.
///
/// Mirrors the FastAPI response shape in app/api/v1/endpoints/lecture.py:
///   GET /{lecture_id}/transcript → List<TranscriptSegment>

class TranscriptSegment {
  final int startSeconds;
  final String timestamp;
  final String text;

  const TranscriptSegment({
    required this.startSeconds,
    required this.timestamp,
    required this.text,
  });

  factory TranscriptSegment.fromJson(Map<String, dynamic> json) {
    return TranscriptSegment(
      startSeconds: (json['start_seconds'] as num?)?.toInt() ?? 0,
      timestamp: json['timestamp'] as String? ?? '',
      text: json['text'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'start_seconds': startSeconds,
    'timestamp': timestamp,
    'text': text,
  };
}
