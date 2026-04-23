import 'dart:io';
import '../models/lecture_models.dart';
import 'package:path_provider/path_provider.dart';

/// Manages local storage of downloaded lecture content files.
/// Files are stored under: <appDocDir>/hololearn_lectures/lecture_{id}/
class LocalFileService {
  static const String _rootFolder = 'hololearn_lectures';

  /// Returns the directory for a specific lecture, creating it if needed.
  static Future<Directory> _lectureDir(int lectureId) async {
    final base = await getApplicationDocumentsDirectory();
    final dir = Directory('${base.path}/$_rootFolder/lecture_$lectureId');
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return dir;
  }

  /// Consistent filename for a content type.
  /// e.g. lecture_42_worksheet.pdf
  static String fileName(int lectureId, GenContentType type) {
  switch (type) {
    case GenContentType.script:
      return 'lecture_${lectureId}_script.txt';
    case GenContentType.knowledgeGraph:
      return 'lecture_${lectureId}_knowledge_graph.html';
    default:
      return 'lecture_${lectureId}_${type.name}.pdf';
  }
}

static Future<File> fileFor(int lectureId, GenContentType type) async {
  final dir = await _lectureDir(lectureId);
  return File('${dir.path}/${fileName(lectureId, type)}');
}

static Future<bool> exists(int lectureId, GenContentType type) async {
  final file = await fileFor(lectureId, type);
  return file.exists();
}

static Future<File> save(
  int lectureId,
  GenContentType type,
  List<int> bytes,
) async {
  final file = await fileFor(lectureId, type);
  await file.writeAsBytes(bytes, flush: true);
  return file;
}

  /// Deletes all cached files for a lecture (e.g. after deletion).
  static Future<void> clearLecture(int lectureId) async {
    final base = await getApplicationDocumentsDirectory();
    final dir = Directory('${base.path}/$_rootFolder/lecture_$lectureId');
    if (await dir.exists()) {
      await dir.delete(recursive: true);
      print('🗑️ Cleared cache for lecture $lectureId');
    }
  }
}
